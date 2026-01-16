"""
Sandbox Mode - умный режим самотестирования агента

НОВЫЙ ПОДХОД:
Вместо тестирования заранее написанных сценариев, sandbox mode:
1. Читает реальные ошибки из production (data/errors/)
2. Генерирует тестовые сценарии на основе этих ошибок
3. Пытается воспроизвести проблемы и найти решения
4. Создаёт детальный отчёт с рекомендациями

Это позволяет агенту "учиться на ошибках" и улучшать свою работу.
"""
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
from src.agent.ai_agent import AIAgent
from src.agent.action_executor import ActionExecutor
from src.agent.supervisor_agent import SupervisorAgent
from src.tools.browser_tools import BrowserTools


class SandboxMode:
    """Умный режим песочницы - учится на реальных ошибках"""

    def __init__(
        self,
        agent: AIAgent,
        executor: ActionExecutor,
        browser_tools: BrowserTools,
        max_tokens: int = 4000,
        output_dir: str = "data/sandbox_reports"
    ):
        self.agent = agent
        self.executor = executor
        self.browser = browser_tools
        self.max_tokens = max_tokens
        self.output_dir = Path(output_dir)
        self.errors_dir = Path("data/errors")
        self.logger = logging.getLogger(__name__)

        # SupervisorAgent в sandbox mode
        self.supervisor = SupervisorAgent(mode="sandbox")

        # Создаём директории
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.errors_dir.mkdir(parents=True, exist_ok=True)

        # Результаты тестирования
        self.test_results: List[Dict[str, Any]] = []
        self.error_sources: List[str] = []  # откуда брали ошибки

    async def run_exploration(self) -> Dict[str, Any]:
        """
        Запустить умное исследование на основе реальных ошибок

        Returns:
            детальный отчёт
        """
        print("\n" + "=" * 70)
        print("🧪 SANDBOX MODE - АНАЛИЗ РЕАЛЬНЫХ ОШИБОК")
        print("=" * 70)
        print("\nАнализирую ошибки из production и генерирую тестовые сценарии.\n")

        # Шаг 1: Загружаем реальные ошибки
        errors = self._load_production_errors()

        if not errors:
            print("📭 Нет зафиксированных ошибок из production.")
            print("   Запустите агента обычным образом (python main.py),")
            print("   после чего можно будет анализировать возникшие проблемы.\n")
            return self._generate_empty_report()

        print(f"📋 Загружено ошибок: {len(errors)}")
        print(f"   Источники: {', '.join(self.error_sources)}\n")

        # Шаг 2: Генерируем тестовые сценарии на основе ошибок
        scenarios = await self._generate_scenarios_from_errors(errors)
        print(f"📝 Сгенерировано тестовых сценариев: {len(scenarios)}\n")

        # Шаг 3: Выполняем тесты
        for i, scenario in enumerate(scenarios, 1):
            print(f"\n{'='*70}")
            print(f"ТЕСТ {i}/{len(scenarios)}: {scenario['name']}")
            print(f"{'='*70}")

            result = await self._run_test_scenario(scenario)
            self.test_results.append(result)

            # Небольшая пауза между тестами
            await asyncio.sleep(1)

        # Генерируем итоговый отчёт
        report = self._generate_report(errors)

        # Сохраняем отчёт
        self._save_report(report)

        return report

    def _load_production_errors(self) -> List[Dict[str, Any]]:
        """
        Загрузить ошибки из production

        Returns:
            список ошибок
        """
        errors = []

        # Ищем все файлы с ошибками
        error_files = list(self.errors_dir.glob("production_*.jsonl")) + \
                      list(self.errors_dir.glob("session_*.json"))

        if not error_files:
            return errors

        for error_file in error_files:
            try:
                self.error_sources.append(error_file.name)

                if error_file.suffix == ".jsonl":
                    # JSONL формат (построчный)
                    with open(error_file, "r", encoding="utf-8") as f:
                        for line in f:
                            if line.strip():
                                errors.append(json.loads(line))
                else:
                    # JSON формат (session summary)
                    with open(error_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if "errors" in data:
                            errors.extend(data["errors"])

            except Exception as e:
                self.logger.error(f"Не удалось загрузить {error_file}: {e}")

        return errors

    async def _generate_scenarios_from_errors(
        self,
        errors: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Генерировать тестовые сценарии на основе реальных ошибок

        Использует LLM для создания умных сценариев

        Args:
            errors: список ошибок из production

        Returns:
            список тестовых сценариев
        """
        # Группируем ошибки по типам действий
        errors_by_action = {}
        for error in errors:
            action = error.get("action", "unknown")
            if action not in errors_by_action:
                errors_by_action[action] = []
            errors_by_action[action].append(error)

        scenarios = []

        # Для каждого типа действия генерируем сценарии
        for action, action_errors in errors_by_action.items():
            # Берём самую свежую ошибку этого типа
            latest_error = max(action_errors, key=lambda e: e.get("timestamp", ""))

            # Генерируем 3 типа сценариев:
            # 1. Воспроизведение ошибки
            scenarios.append({
                "type": "reproduction",
                "name": f"Воспроизвести: {action} с теми же параметрами",
                "action": action,
                "params": latest_error.get("params", {}),
                "original_error": latest_error,
                "expected": "should_fail"
            })

            # 2. Попытка с альтернативными параметрами
            alternative_params = await self._generate_alternative_params(
                action,
                latest_error.get("params", {}),
                latest_error.get("error_message", "")
            )

            if alternative_params:
                scenarios.append({
                    "type": "alternative",
                    "name": f"Альтернатива: {action} с другими параметрами",
                    "action": action,
                    "params": alternative_params,
                    "original_error": latest_error,
                    "expected": "should_succeed"
                })

            # 3. Проверка на разных страницах (если есть URL в контексте)
            if latest_error.get("params", {}).get("url"):
                scenarios.append({
                    "type": "cross_site",
                    "name": f"Проверка: {action} на другом сайте",
                    "action": action,
                    "params": latest_error.get("params", {}),
                    "original_error": latest_error,
                    "expected": "check_consistency"
                })

        return scenarios

    async def _generate_alternative_params(
        self,
        action: str,
        original_params: Dict[str, Any],
        error_message: str
    ) -> Optional[Dict[str, Any]]:
        """
        Сгенерировать альтернативные параметры для действия

        Использует LLM для умной генерации альтернатив

        Args:
            action: название действия
            original_params: оригинальные параметры
            error_message: сообщение об ошибке

        Returns:
            альтернативные параметры или None
        """
        # Простая эвристика (можно улучшить с LLM)
        alternatives = {}

        if action == "click_by_text":
            # Если кликали по тексту - пробуем с exact=False
            text = original_params.get("text", "")
            alternatives = {
                "text": text,
                "exact": not original_params.get("exact", False)
            }

        elif action == "type_text":
            # Пробуем другой селектор
            alternatives = original_params.copy()
            # Можно добавить логику поиска альтернативных селекторов

        elif action == "wait_for_text":
            # Увеличиваем таймаут
            alternatives = original_params.copy()
            alternatives["timeout"] = original_params.get("timeout", 5000) * 2

        return alternatives if alternatives else None

    async def _run_test_scenario(self, scenario: Dict[str, Any]) -> Dict[str, Any]:
        """
        Выполнить тестовый сценарий

        Args:
            scenario: сценарий для выполнения

        Returns:
            результат выполнения
        """
        start_time = datetime.now()

        result = {
            "scenario": scenario["name"],
            "type": scenario["type"],
            "action": scenario["action"],
            "params": scenario["params"],
            "timestamp": start_time.isoformat(),
            "status": "unknown",
            "error": None,
            "duration_ms": 0,
            "original_error": scenario.get("original_error")
        }

        try:
            print(f"   🔧 Выполнение: {scenario['action']}")
            print(f"      Параметры: {scenario['params']}")
            print(f"      Ожидание: {scenario['expected']}")

            # Выполняем через supervisor (он будет логировать)
            action_result = await self.supervisor.supervised_execute(
                self.executor,
                {
                    "action": scenario["action"],
                    "params": scenario["params"],
                    "reasoning": f"Sandbox тест: {scenario['type']}"
                }
            )

            # Анализируем результат
            status = action_result.get("status")
            expected = scenario.get("expected")

            if status == "success":
                if expected == "should_fail":
                    result["status"] = "unexpected_success"
                    result["note"] = "Ошибка НЕ воспроизведена (возможно исправлена?)"
                    print(f"   ⚠️  Неожиданный успех: ошибка не воспроизводится")
                else:
                    result["status"] = "success"
                    print(f"   ✅ Успех")

            elif status == "error":
                if expected == "should_fail":
                    result["status"] = "expected_fail"
                    result["note"] = "Ошибка воспроизведена как ожидалось"
                    print(f"   ✅ Ошибка воспроизведена (ожидалось)")
                elif expected == "should_succeed":
                    result["status"] = "failed"
                    result["error"] = action_result.get("message")
                    result["note"] = "Альтернатива не сработала"
                    print(f"   ❌ Альтернатива не помогла: {result['error']}")
                else:
                    result["status"] = "failed"
                    result["error"] = action_result.get("message")
                    print(f"   ❌ Ошибка: {result['error']}")

        except Exception as e:
            result["status"] = "exception"
            result["error"] = str(e)
            result["error_type"] = type(e).__name__
            print(f"   💥 Исключение: {e}")
            self.logger.error(f"Исключение в сценарии {scenario['name']}: {e}", exc_info=True)

        # Вычисляем длительность
        end_time = datetime.now()
        result["duration_ms"] = int((end_time - start_time).total_seconds() * 1000)

        return result

    def _generate_report(self, source_errors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Сгенерировать итоговый отчёт

        Args:
            source_errors: оригинальные ошибки из production

        Returns:
            детальный отчёт
        """
        total_tests = len(self.test_results)

        # Подсчёт статистики
        reproduction_tests = [r for r in self.test_results if r["type"] == "reproduction"]
        alternative_tests = [r for r in self.test_results if r["type"] == "alternative"]

        reproduced = sum(1 for r in reproduction_tests if r["status"] == "expected_fail")
        fixed = sum(1 for r in reproduction_tests if r["status"] == "unexpected_success")
        alternatives_worked = sum(1 for r in alternative_tests if r["status"] == "success")

        # Формируем findings
        findings = {
            "total_production_errors": len(source_errors),
            "errors_reproduced": reproduced,
            "errors_possibly_fixed": fixed,
            "working_alternatives_found": alternatives_worked,
            "reproduction_rate": round((reproduced / len(reproduction_tests) * 100) if reproduction_tests else 0, 2)
        }

        # Рекомендации
        recommendations = []

        if fixed > 0:
            recommendations.append(
                f"🎉 {fixed} ошибок больше не воспроизводятся! Возможно были исправлены."
            )

        if alternatives_worked > 0:
            recommendations.append(
                f"💡 Найдено {alternatives_worked} работающих альтернатив для проблемных действий."
            )

        if reproduced == len(reproduction_tests) and reproduced > 0:
            recommendations.append(
                "⚠️ Все ошибки воспроизводятся. Требуется исправление кода."
            )

        report = {
            "timestamp": datetime.now().isoformat(),
            "mode": "smart_sandbox",
            "based_on_errors": self.error_sources,
            "summary": {
                "total_tests": total_tests,
                "reproduction_tests": len(reproduction_tests),
                "alternative_tests": len(alternative_tests),
            },
            "findings": findings,
            "recommendations": recommendations,
            "detailed_results": self.test_results,
            "supervisor_stats": self.supervisor.get_statistics()
        }

        return report

    def _generate_empty_report(self) -> Dict[str, Any]:
        """Сгенерировать пустой отчёт (когда нет ошибок)"""
        return {
            "timestamp": datetime.now().isoformat(),
            "mode": "smart_sandbox",
            "based_on_errors": [],
            "summary": {
                "total_tests": 0,
                "reproduction_tests": 0,
                "alternative_tests": 0,
            },
            "findings": {
                "total_production_errors": 0,
                "message": "Нет ошибок для анализа"
            },
            "recommendations": [
                "Запустите агента в обычном режиме для сбора данных об ошибках"
            ],
            "detailed_results": []
        }

    def _save_report(self, report: Dict[str, Any]):
        """Сохранить отчёт в файл"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.output_dir / f"sandbox_report_{timestamp}.json"

        try:
            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)

            print(f"\n📄 Отчёт сохранён: {report_file}")
            self.logger.info(f"Sandbox report saved to {report_file}")

        except Exception as e:
            self.logger.error(f"Ошибка сохранения отчёта: {e}")
            print(f"\n❌ Не удалось сохранить отчёт: {e}")

    def print_summary(self, report: Dict[str, Any]):
        """Вывести краткую сводку результатов"""
        summary = report["summary"]
        findings = report["findings"]

        print("\n" + "=" * 70)
        print("📊 ИТОГОВАЯ СВОДКА")
        print("=" * 70)

        if findings.get("total_production_errors", 0) == 0:
            print("\n📭 Нет ошибок для анализа.")
            print("   Запустите агента в обычном режиме (python main.py)")
            print("   чтобы собрать данные об ошибках.\n")
            return

        print(f"\n📋 Проанализировано ошибок из production: {findings['total_production_errors']}")
        print(f"🧪 Выполнено тестов: {summary['total_tests']}")
        print(f"   - Воспроизведение: {summary['reproduction_tests']}")
        print(f"   - Альтернативы: {summary['alternative_tests']}")

        print("\n🔍 РЕЗУЛЬТАТЫ:")
        print(f"   ✅ Ошибок воспроизведено: {findings['errors_reproduced']}")
        print(f"   🎉 Ошибок возможно исправлено: {findings['errors_possibly_fixed']}")
        print(f"   💡 Работающих альтернатив найдено: {findings['working_alternatives_found']}")
        print(f"   📊 Процент воспроизведения: {findings['reproduction_rate']}%")

        if report.get("recommendations"):
            print("\n💡 РЕКОМЕНДАЦИИ:")
            for rec in report["recommendations"]:
                print(f"   {rec}")

        print("\n" + "=" * 70)
