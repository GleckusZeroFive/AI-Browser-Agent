"""
SupervisorAgent - реактивный наблюдатель за работой агента

Активируется ТОЛЬКО при ошибках (не тратит токены постоянно).
Анализирует runtime errors с помощью LLM и фиксирует их для дальнейшего анализа.

Режимы работы:
- production: краткий анализ + взаимодействие с пользователем
- sandbox: детальный анализ + автоматическое продолжение
"""
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from src.agent.ai_agent import AIAgent
from src.utils.bug_tracker import BugTracker


class SupervisorAgent:
    """
    Реактивный supervisor - активируется только при ошибках

    Не делает постоянных LLM вызовов - экономит токены!
    Просыпается только когда что-то пошло не так.
    """

    def __init__(self, mode: str = "production"):
        """
        Args:
            mode: "production" или "sandbox"
        """
        self.mode = mode
        self.logger = logging.getLogger(__name__)

        # Ленивая инициализация AI агента (создаётся при первой ошибке)
        self.ai_agent: Optional[AIAgent] = None

        # Статистика
        self.error_count = 0
        self.runtime_errors_count = 0
        self.structured_errors_count = 0

        # Директории для логирования
        self.errors_dir = Path("data/errors")
        self.errors_dir.mkdir(parents=True, exist_ok=True)

        # Текущая сессия (для production mode)
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_errors: list = []

        # Bug Tracker - интегрированная система отслеживания lifecycle багов
        self.bug_tracker = BugTracker()

    async def supervised_execute(self, executor, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обёртка над ActionExecutor.execute() с перехватом ошибок

        Supervisor НЕ наблюдает постоянно - он спит до момента ошибки!

        Args:
            executor: ActionExecutor instance
            action: действие для выполнения

        Returns:
            результат выполнения (с анализом ошибки если была)
        """
        try:
            # Обычное выполнение - supervisor спит 😴
            result = await executor.execute(action)

            # Проверяем статус (БЕЗ LLM!)
            if result.get("status") == "error":
                # Structured error от ActionExecutor - легковесная обработка
                return await self._handle_structured_error(result, action)

            return result

        except Exception as runtime_error:
            # ЗДЕСЬ supervisor просыпается! 🚨
            # Только СЕЙЧАС делаем LLM вызов
            return await self._handle_runtime_error(runtime_error, action)

    async def _handle_structured_error(
        self,
        result: Dict[str, Any],
        action: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Обработка structured error (status: "error")

        Уже есть описание ошибки от ActionExecutor
        НЕ нужен LLM анализ - просто логируем

        Args:
            result: результат с ошибкой
            action: действие которое вызвало ошибку

        Returns:
            result (без изменений или с дополнениями)
        """
        self.error_count += 1
        self.structured_errors_count += 1

        error_data = {
            "type": "structured",
            "timestamp": datetime.now().isoformat(),
            "action": action.get("action"),
            "params": action.get("params", {}),
            "reasoning": action.get("reasoning", ""),
            "error_type": result.get("error_type"),
            "error_message": result.get("message"),
            "suggestion": result.get("suggestion")
        }

        # Логируем в файл
        self._log_error(error_data)

        # 🆕 Регистрируем в Bug Tracker
        bug_id = self.bug_tracker.report_bug(
            error_data=error_data,
            session_id=self.session_id,
            source=self.mode
        )
        self.logger.info(f"Structured error registered as bug: {bug_id}")

        # В production mode - показываем пользователю
        if self.mode == "production":
            self.logger.warning(f"Structured error: {error_data['error_message']}")

            # Добавляем в сессию для потенциального sandbox анализа
            self.session_errors.append(error_data)

        # Возвращаем результат без изменений
        return result

    async def _handle_runtime_error(
        self,
        error: Exception,
        action: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Обработка runtime error (неожиданное исключение)

        НУЖЕН LLM анализ для понимания что произошло

        Args:
            error: исключение
            action: действие которое вызвало ошибку

        Returns:
            structured response с анализом
        """
        self.error_count += 1
        self.runtime_errors_count += 1

        self.logger.error(
            f"Runtime error in {action.get('action')}: {error}",
            exc_info=True
        )

        # Ленивая инициализация AI агента
        if not self.ai_agent:
            self.ai_agent = AIAgent()
            self.logger.info("SupervisorAgent AI initialized (first runtime error)")

        # Формируем контекст для LLM анализа
        context = self._build_error_context(error, action)

        # LLM анализ (ТОЛЬКО для runtime errors)
        analysis = await self._analyze_with_llm(context)

        # Подготовка данных для логирования
        error_data = {
            "type": "runtime",
            "timestamp": datetime.now().isoformat(),
            "action": action.get("action"),
            "params": action.get("params", {}),
            "reasoning": action.get("reasoning", ""),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "analysis": analysis
        }

        # Логируем с анализом
        await self._log_analyzed_error(error_data)

        # 🆕 Регистрируем в Bug Tracker
        bug_id = self.bug_tracker.report_bug(
            error_data=error_data,
            session_id=self.session_id,
            source=self.mode
        )
        self.logger.info(f"Runtime error registered as bug: {bug_id}")

        # В production mode - спрашиваем пользователя
        if self.mode == "production":
            await self._report_to_user(error_data)

            # Добавляем в сессию
            self.session_errors.append(error_data)

        # Возвращаем structured response
        return {
            "status": "error",
            "error_type": "runtime_error",
            "message": analysis.get("user_message", str(error)),
            "suggestion": analysis.get("suggestion", "Попробуйте другой подход"),
            "supervisor_analysis": analysis
        }

    def _build_error_context(self, error: Exception, action: Dict[str, Any]) -> str:
        """
        Построить контекст для LLM анализа ошибки

        Args:
            error: исключение
            action: действие

        Returns:
            текстовый контекст для LLM
        """
        context = f"""# RUNTIME ERROR ANALYSIS

## Действие агента
- Action: {action.get('action')}
- Parameters: {json.dumps(action.get('params', {}), ensure_ascii=False, indent=2)}
- Reasoning: {action.get('reasoning', 'не указано')}

## Ошибка
- Type: {type(error).__name__}
- Message: {str(error)}

## Твоя задача
Проанализируй ошибку и ответь в формате JSON:
{{
  "root_cause": "Краткое объяснение причины ошибки",
  "user_message": "Понятное сообщение для пользователя (НЕ технический текст)",
  "suggestion": "Что можно попробовать дальше",
  "is_critical": true/false,
  "reproducible_scenario": "Краткий сценарий для воспроизведения"
}}
"""
        return context

    async def _analyze_with_llm(self, context: str) -> Dict[str, Any]:
        """
        Анализ ошибки с помощью LLM

        Args:
            context: контекст для анализа

        Returns:
            результат анализа
        """
        try:
            response = self.ai_agent.chat(context)

            # Пытаемся распарсить JSON
            # Ищем JSON в ответе (между { и })
            import re
            json_match = re.search(r'\{.*\}', response, re.DOTALL)

            if json_match:
                analysis = json.loads(json_match.group())
                return analysis
            else:
                # Не смогли распарсить - возвращаем базовый анализ
                self.logger.warning("LLM не вернул валидный JSON, использую fallback")
                return {
                    "root_cause": "Не удалось проанализировать",
                    "user_message": "Произошла внутренняя ошибка",
                    "suggestion": "Попробуйте переформулировать запрос",
                    "is_critical": False,
                    "reproducible_scenario": "N/A"
                }

        except Exception as e:
            self.logger.error(f"Ошибка при LLM анализе: {e}", exc_info=True)
            return {
                "root_cause": f"Ошибка анализа: {e}",
                "user_message": "Произошла внутренняя ошибка",
                "suggestion": "Попробуйте ещё раз",
                "is_critical": False,
                "reproducible_scenario": "N/A"
            }

    def _log_error(self, error_data: Dict[str, Any]):
        """
        Простое логирование ошибки в файл (БЕЗ анализа)

        Args:
            error_data: данные об ошибке
        """
        log_file = self.errors_dir / f"{self.mode}_{self.session_id}.jsonl"

        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(error_data, ensure_ascii=False) + "\n")
        except Exception as e:
            self.logger.error(f"Не удалось записать лог ошибки: {e}")

    async def _log_analyzed_error(self, error_data: Dict[str, Any]):
        """
        Логирование ошибки с LLM анализом

        Args:
            error_data: данные об ошибке с анализом
        """
        # Логируем в основной файл
        self._log_error(error_data)

        # В sandbox mode - дополнительно создаём детальный отчёт
        if self.mode == "sandbox":
            detail_file = self.errors_dir / f"sandbox_detail_{self.session_id}.json"

            try:
                # Загружаем существующие данные если есть
                if detail_file.exists():
                    with open(detail_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                else:
                    data = {"errors": []}

                data["errors"].append(error_data)

                with open(detail_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

            except Exception as e:
                self.logger.error(f"Не удалось записать детальный лог: {e}")

    async def _report_to_user(self, error_data: Dict[str, Any]):
        """
        Сообщить пользователю об ошибке (production mode)

        Args:
            error_data: данные об ошибке
        """
        analysis = error_data.get("analysis", {})

        print("\n" + "=" * 70)
        print("⚠️  SUPERVISOR: Обнаружена проблема")
        print("=" * 70)
        print(f"\n{analysis.get('user_message', 'Произошла ошибка')}")

        if analysis.get("suggestion"):
            print(f"\n💡 Рекомендация: {analysis['suggestion']}")

        print("\n📋 Проблема зафиксирована для разработчиков.")

        # Опционально: спрашиваем у пользователя дополнительный контекст
        if analysis.get("is_critical"):
            print("\n🚨 Это критическая ошибка. Есть что добавить о ситуации?")
            print("   (нажмите Enter чтобы пропустить)")

            try:
                import asyncio
                user_context = await asyncio.to_thread(input, "   Ваш комментарий: ")

                if user_context.strip():
                    error_data["user_context"] = user_context
                    self.logger.info(f"Пользовательский контекст: {user_context}")

                    # Обновляем лог с контекстом
                    self._log_error(error_data)

            except Exception as e:
                self.logger.error(f"Ошибка при получении контекста от пользователя: {e}")

        print("=" * 70 + "\n")

    def save_session_summary(self):
        """
        Сохранить итоговую сводку по сессии (для production mode)

        Вызывается при завершении работы агента
        """
        if self.mode != "production" or not self.session_errors:
            return

        summary_file = self.errors_dir / f"session_{self.session_id}.json"

        try:
            summary = {
                "session_id": self.session_id,
                "timestamp": datetime.now().isoformat(),
                "total_errors": self.error_count,
                "runtime_errors": self.runtime_errors_count,
                "structured_errors": self.structured_errors_count,
                "errors": self.session_errors
            }

            with open(summary_file, "w", encoding="utf-8") as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)

            self.logger.info(f"Session summary saved: {summary_file}")

            # Если были ошибки - подсказываем про sandbox mode
            if self.error_count > 0:
                print(f"\n💡 Обнаружено ошибок: {self.error_count}")
                print(f"   Запустите 'python main.py --sandbox' для автоматического анализа")

        except Exception as e:
            self.logger.error(f"Не удалось сохранить session summary: {e}")

    def get_statistics(self) -> Dict[str, Any]:
        """
        Получить статистику работы supervisor

        Returns:
            словарь со статистикой
        """
        return {
            "mode": self.mode,
            "session_id": self.session_id,
            "total_errors": self.error_count,
            "runtime_errors": self.runtime_errors_count,
            "structured_errors": self.structured_errors_count,
            "ai_agent_initialized": self.ai_agent is not None
        }
