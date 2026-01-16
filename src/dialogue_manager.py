"""
DialogueManager - главный оркестратор диалоговой системы
Управляет циклом: пользователь → AI → действие → результат
"""
import asyncio
import logging
import re
import time
from typing import Optional
from datetime import datetime
from src.agent.ai_agent import AIAgent
from src.agent.action_executor import ActionExecutor
from src.agent.supervisor_agent import SupervisorAgent
from src.tools.browser_tools import BrowserTools
from src.config import Config
from src.agent.specialized_agents import AgentSelector, TaskType
from src.agent.knowledge_base import KnowledgeBase
from src.utils.log_setup import LogSetup

class DialogueManager:
    """Менеджер диалога пользователя с AI агентом"""

    def __init__(self):
        self.agent = AIAgent()
        self.browser_tools = BrowserTools()
        self.executor = ActionExecutor(self.browser_tools)
        self.browser_started = False

        # SupervisorAgent: реактивный наблюдатель за ошибками
        self.supervisor = SupervisorAgent(mode="production")

        # Knowledge Base: долговременная память агента
        self.knowledge_base: Optional[KnowledgeBase] = None

        # Sub-agent architecture: отслеживание текущего специализированного агента
        self.current_task_type = TaskType.GENERAL
        self.current_specialized_agent = None

        # Настройка логирования
        self._setup_logging()

        # Путь к файлу для логирования ответов агента
        self.agent_responses_log = LogSetup.setup_agent_response_log()

    async def start(self, sandbox_mode: bool = False):
        """Запустить диалоговую систему"""
        print("=" * 70)
        print("🤖 AI BROWSER AGENT")
        print("=" * 70)

        # Инициализируем knowledge base (долговременная память)
        self.knowledge_base = KnowledgeBase(
            llm_client=self.agent.client,
            storage_path="data/knowledge_base.json"
        )

        # Очищаем working_memory от прошлой сессии (предотвращает галлюцинации)
        self.knowledge_base.clear_working_memory()

        # НОВОЕ: Подключаем KB к агенту для оптимизации контекста
        self.agent.knowledge_base = self.knowledge_base

        # Инициализируем агента с системным промптом
        self.agent.add_system_prompt()

        print("📚 База знаний загружена (working memory очищена)")

        # Запускаем браузер
        print("\n🌐 Запускаю браузер...")
        await self.browser_tools.start_browser(headless=Config.BROWSER_HEADLESS)
        self.browser_started = True
        print("✓ Браузер готов\n")

        # Если sandbox mode - запускаем тестирование
        if sandbox_mode:
            await self._run_sandbox_mode()
            return

        # ПРИВЕТСТВИЕ ОТ АГЕНТА
        print("🤖 Агент: Привет! Я AI-агент для двух задач:")
        print("   🌤️  Погода (yandex.ru/pogoda)")
        print("   🍕 Пицца (Додопицца)")
        print("\n   Что хочешь узнать?\n")
        print("(Напиши задачу или 'exit' для выхода)\n")

        # Главный цикл диалога
        try:
            await self._dialogue_loop()
        finally:
            await self._cleanup()

    async def _run_sandbox_mode(self):
        """Запустить режим песочницы для самотестирования"""
        from src.utils.sandbox_mode import SandboxMode

        # Создаём sandbox с увеличенными токенами
        sandbox = SandboxMode(
            agent=self.agent,
            executor=self.executor,
            browser_tools=self.browser_tools,
            max_tokens=4000
        )

        # Запускаем исследование
        report = await sandbox.run_exploration()

        # Выводим сводку
        sandbox.print_summary(report)

        print("\n💡 Sandbox mode завершён. Отчёт сохранён в data/sandbox_reports/")
        print("   Используйте его для анализа проблем с инструментами.\n")

    async def _dialogue_loop(self):
        """Основной цикл диалога с улучшенной обработкой ошибок"""
        while True:
            try:
                # Получаем ввод пользователя с таймаутом и keepalive
                user_input = await self._get_user_input_with_timeout()

                # Проверка на таймаут
                if user_input is None:
                    print("\n👋 Завершаю сессию из-за неактивности. До встречи!")
                    self.logger.info("Завершение из-за таймаута")
                    break

                # Проверка на выход (с учётом фраз типа "Спасибо. Пока")
                if self._is_exit_command(user_input):
                    print("\n👋 До встречи!")
                    self.logger.info("Завершение по команде пользователя")
                    break

                if not user_input.strip():
                    continue

                self.logger.info(f"Пользователь: {user_input}")

                # Автоматический выбор специализированного агента
                task_type, specialized_agent = AgentSelector.select_agent(user_input)

                # Если тип задачи изменился - переключаем агента
                if task_type != self.current_task_type:
                    self.current_task_type = task_type
                    self.current_specialized_agent = specialized_agent

                    # НОВОЕ: Уведомляем AIAgent о смене типа задачи
                    if task_type == TaskType.SHOPPING:
                        self.agent.set_task_type("shopping")
                    elif task_type == TaskType.EMAIL:
                        self.agent.set_task_type("email")
                    elif task_type == TaskType.JOB_SEARCH:
                        self.agent.set_task_type("job_search")
                    else:
                        self.agent.set_task_type(None)

                    # Логируем переключение
                    if specialized_agent:
                        agent_name = specialized_agent.__class__.__name__
                        self.logger.info(f"Переключение на специализированного агента: {agent_name}")
                        print(f"🔄 Активирован специализированный агент: {agent_name}")

                        # ИСПРАВЛЕНИЕ: НЕ пересоздаём агента! Только обновляем системный промпт
                        # Это сохраняет всю историю разговора
                        system_prompt = specialized_agent.get_system_prompt()

                        # Проверяем размер промпта и выбираем подходящую модель
                        prompt_tokens = self.agent._estimate_tokens(system_prompt)
                        self.logger.info(f"Размер промпта {agent_name}: {prompt_tokens} токенов")

                        # Выбираем модель с достаточным лимитом
                        suggested_model = specialized_agent.get_model()
                        model_limit = Config.MODEL_TOKEN_LIMITS.get(suggested_model, 6000)
                        safe_limit = int(model_limit * Config.SAFE_TOKEN_MARGIN)

                        if prompt_tokens > safe_limit:
                            self.logger.warning(
                                f"Промпт ({prompt_tokens} токенов) превышает безопасный лимит модели "
                                f"{suggested_model} ({safe_limit} токенов)"
                            )
                            # Ищем модель с большим лимитом
                            suitable_model = self.agent._get_suitable_fallback_model(
                                prompt_tokens * 2,  # Умножаем на 2 для запаса под историю
                                exclude_model=None
                            )
                            if suitable_model:
                                self.logger.info(f"Переключение на модель с большим лимитом: {suitable_model}")
                                print(f"💡 Используется модель с большим лимитом токенов: {suitable_model}")
                                self.agent.current_model = suitable_model
                            else:
                                self.logger.warning("Не найдена подходящая модель, используем модель по умолчанию")
                                self.agent.current_model = suggested_model
                        else:
                            self.agent.current_model = suggested_model

                        # ИСПРАВЛЕНИЕ: Обновляем системный промпт вместо добавления нового
                        # Используем встроенный метод для обновления
                        self.agent._update_system_message(system_prompt)
                        self.agent._cached_system_prompt = system_prompt
                        self.agent._cached_prompt_level = None  # Инвалидируем кеш

                        # Подключаем KB если отключена
                        if not self.agent.knowledge_base:
                            self.agent.knowledge_base = self.knowledge_base
                    else:
                        self.logger.info("Используется общий агент (GENERAL)")
                        # ИСПРАВЛЕНИЕ: НЕ пересоздаём агента, только обновляем промпт
                        base_prompt = self.agent._get_base_system_prompt(self.agent._current_prompt_level)
                        self.agent._update_system_message(base_prompt)
                        self.agent._cached_system_prompt = base_prompt

                # НОВОЕ: Обновляем knowledge base
                if self.knowledge_base:
                    await self.knowledge_base.extract_and_update(user_input, "")

                # Отправляем в AI агента
                # НОВОЕ: agent сам выберет оптимальный уровень контекста
                print("\n🤖 Агент думает...")

                try:
                    response = self.agent.chat(
                        user_input,
                        context=None,  # Пока без контекста страницы
                        specialized_agent=self.current_specialized_agent
                    )
                    self.logger.info(f"Агент ответил: {response[:100]}...")

                    # НОВОЕ: Показываем статистику токенов (если DEBUG режим)
                    if Config.DEBUG_MODE:
                        self._print_token_stats()

                    # Knowledge Base: обновляем после получения ответа
                    if self.knowledge_base:
                        await self.knowledge_base.extract_and_update(user_input, response)

                except Exception as api_error:
                    self.logger.error(f"Ошибка API: {api_error}", exc_info=True)
                    print(f"\n❌ Ошибка связи с API: {api_error}")
                    print("Попробуйте ещё раз.\n")
                    continue

                # ЛОГИРОВАНИЕ: Сохраняем полный ответ агента
                with open(self.agent_responses_log, "a", encoding="utf-8") as f:
                    f.write(f"\n{'='*60}\n")
                    f.write(f"USER: {user_input}\n")
                    f.write(f"AGENT RESPONSE:\n{response}\n")

                # ПРОВЕРКА ГАЛЛЮЦИНАЦИЙ: если агент утверждает что-то - проверяем базу знаний
                if self.knowledge_base and self.knowledge_base.should_verify_before_claiming(response):
                    self.logger.warning("Агент делает утверждение - требуется проверка")
                    # Извлекаем что именно агент утверждает
                    needs_verification = True
                    with open(self.agent_responses_log, "a", encoding="utf-8") as f:
                        f.write(f"⚠️  ТРЕБУЕТСЯ ПРОВЕРКА УТВЕРЖДЕНИЯ\n")
                else:
                    needs_verification = False

                # Проверяем, это диалог или действие?
                action = self.agent.parse_action(response)

                # НОВОЕ: Автоматически обновляем working_memory на основе ответа агента
                await self._update_working_memory_from_response(user_input, response, action)

                # ЛОГИРОВАНИЕ: Результат парсинга
                with open(self.agent_responses_log, "a", encoding="utf-8") as f:
                    if action:
                        f.write(f"PARSED ACTION: {action}\n")
                    else:
                        f.write(f"NO ACTION PARSED (dialogue mode)\n")

                if action:
                    # Проверка на ошибочное использование "dialog"
                    if action.get("action") == "dialog":
                        # Graceful fallback: извлекаем текст и выводим как диалог
                        self.logger.warning("Агент использовал action='dialog' (не существует). Извлекаю текст.")

                        # Извлекаем текст из разных возможных полей
                        dialog_text = (
                            action.get("text") or
                            action.get("params", {}).get("message") or
                            action.get("params", {}).get("text") or
                            "Извините, произошла внутренняя ошибка."
                        )

                        print(f"\n🤖 Агент: {dialog_text}\n")

                    else:
                        # Обычное действие - выполняем команду
                        # Извлекаем текст до JSON
                        text_before_json = response.split('{')[0].strip()
                        if text_before_json:
                            print(f"\n🤖 Агент: {text_before_json}")

                        # Показываем что будет выполнено
                        action_name = action.get("action", "unknown")
                        reasoning = action.get("reasoning", "")
                        print(f"⚙️  Выполняю действие: {action_name}")
                        if reasoning:
                            print(f"   Причина: {reasoning}")

                        await self._execute_action_with_followup(action)

                else:
                    # Режим диалога
                    # Если агент утверждает факт - предупреждаем о необходимости проверки
                    if needs_verification:
                        print(f"\n🤖 Агент: {response}")
                        print("\n⚠️  ВНИМАНИЕ: Агент делает утверждение о существовании чего-либо.")
                        print("    Попросите агента проверить эту информацию или уточните детали.\n")
                    else:
                        print(f"\n🤖 Агент: {response}\n")

            except KeyboardInterrupt:
                print("\n\n👋 Прервано пользователем. До встречи!")
                self.logger.info("Прервано пользователем (Ctrl+C)")
                break
            except Exception as e:
                self.logger.error(f"Ошибка в цикле диалога: {e}", exc_info=True)
                print(f"\n❌ Ошибка: {e}")
                print("Продолжаю работу...\n")
                continue

    def _is_destructive_action(self, action: dict) -> bool:
        """
        Проверить, является ли действие деструктивным (требует подтверждения)

        Деструктивные действия:
        - Оплата и финальное подтверждение заказа
        - Удаление писем/данных
        - Отправка форм (отклики на вакансии)
        - Изменение настроек аккаунта

        Args:
            action: действие для проверки

        Returns:
            bool: True если действие деструктивное
        """
        action_name = action.get("action", "").lower()
        params = action.get("params", {})
        reasoning = action.get("reasoning", "").lower()

        # Ключевые слова для деструктивных действий
        destructive_keywords = {
            # Финансовые операции
            "оплат", "купить", "заказать", "подтвердить заказ", "оформить",
            "pay", "payment", "checkout", "confirm order", "purchase",

            # Удаление данных
            "удал", "delete", "remove", "trash", "корзина",

            # Отправка данных
            "отправить", "откликнуться", "send", "submit", "apply",

            # Изменение настроек
            "изменить пароль", "change password", "delete account"
        }

        # Проверяем текст в reasoning и параметрах
        text_to_check = f"{reasoning} {str(params)}"

        for keyword in destructive_keywords:
            if keyword in text_to_check:
                return True

        # Специфичные действия по типу
        if action_name == "click_by_text":
            button_text = params.get("text", "").lower()

            # Опасные кнопки
            dangerous_buttons = [
                "оплатить", "подтвердить", "удалить", "отправить",
                "откликнуться", "купить", "заказать",
                "pay", "confirm", "delete", "send", "apply", "purchase"
            ]

            for dangerous in dangerous_buttons:
                if dangerous in button_text:
                    return True

        return False

    async def _ask_user_confirmation(self, action: dict) -> bool:
        """
        Запросить подтверждение деструктивного действия у пользователя

        Args:
            action: действие требующее подтверждения

        Returns:
            bool: True если пользователь подтвердил, False если отказался
        """
        action_name = action.get("action", "unknown")
        params = action.get("params", {})
        reasoning = action.get("reasoning", "Нет описания")

        # Формируем понятное описание действия
        print("\n" + "=" * 70)
        print("⚠️  ТРЕБУЕТСЯ ПОДТВЕРЖДЕНИЕ")
        print("=" * 70)
        print(f"\n🔍 Действие: {action_name}")
        print(f"📝 Описание: {reasoning}")
        print(f"⚙️  Параметры: {params}")
        print("\n" + "=" * 70)

        # Определяем тип действия для специального предупреждения
        reasoning_lower = reasoning.lower()
        params_str = str(params).lower()

        if any(kw in reasoning_lower or kw in params_str for kw in ["оплат", "купить", "pay", "purchase"]):
            print("💰 ЭТО ФИНАНСОВАЯ ОПЕРАЦИЯ!")
            print("   После подтверждения может быть списана оплата.")

        elif any(kw in reasoning_lower or kw in params_str for kw in ["удал", "delete"]):
            print("🗑️  ЭТО УДАЛЕНИЕ ДАННЫХ!")
            print("   После подтверждения данные могут быть потеряны.")

        elif any(kw in reasoning_lower or kw in params_str for kw in ["отправ", "send", "submit"]):
            print("📤 ЭТО ОТПРАВКА ДАННЫХ!")
            print("   После подтверждения форма будет отправлена.")

        print("\n" + "=" * 70)

        # Запрашиваем подтверждение
        while True:
            try:
                user_response = await asyncio.to_thread(
                    input,
                    "Подтвердите действие (yes/no): "
                )
                user_response = user_response.strip().lower()

                if user_response in ["yes", "y", "да", "д"]:
                    self.logger.info(f"Пользователь подтвердил деструктивное действие: {action_name}")
                    print("✅ Действие подтверждено. Выполняю...\n")
                    return True
                elif user_response in ["no", "n", "нет", "н"]:
                    self.logger.info(f"Пользователь отклонил деструктивное действие: {action_name}")
                    print("❌ Действие отменено.\n")
                    return False
                else:
                    print("⚠️  Введите 'yes' или 'no'")

            except Exception as e:
                self.logger.error(f"Ошибка при запросе подтверждения: {e}")
                print(f"❌ Ошибка: {e}")
                return False

    async def _execute_action_with_followup(self, action: dict):
        """
        Выполнить действие и продолжить цепочку
        С улучшенной обработкой ошибок, retry логикой и автоматическим продолжением

        Агент может давать команды последовательно.
        После каждого действия проверяем, нужно ли что-то ещё.

        Если агент достиг лимита действий но НЕ дал финального результата,
        автоматически продолжаем с нового цикла.
        """
        max_actions_per_cycle = 10  # Действий в одном цикле
        max_cycles = 3  # Максимум циклов (итого 30 действий)

        actions_count = 0
        cycle_count = 0
        total_actions = 0

        current_action = action

        # Главный цикл с автоматическим продолжением
        while current_action and cycle_count < max_cycles:
            try:
                # Проверяем состояние браузера ПЕРЕД действием
                if not self.browser_started:
                    print("\n⚠️  Браузер не запущен. Пропускаю действие.")
                    self.logger.warning("Попытка выполнить действие без браузера")
                    break

                # SECURITY LAYER: Проверка на деструктивные действия
                if self._is_destructive_action(current_action):
                    confirmed = await self._ask_user_confirmation(current_action)

                    if not confirmed:
                        # Пользователь отказался - прерываем цепочку
                        print("🤖 Агент: Действие отменено по вашему запросу.\n")
                        self.logger.info("Действие отменено пользователем через security layer")
                        break

                # Выполняем действие через Supervisor (перехватывает ошибки)
                self.logger.info(f"Выполняю действие: {current_action.get('action')}")
                result = await self.supervisor.supervised_execute(self.executor, current_action)

                # Проверяем результат - завершение задачи (done/respond/stop)
                if result.get("status") == "done":
                    done_message = result.get("message", "Задача выполнена")
                    print(f"\n🤖 Агент: {done_message}\n")
                    self.logger.info(f"Задача завершена агентом: {done_message}")
                    break  # Выходим из цикла действий

                # Проверяем результат на критические ошибки
                if result.get("status") == "error":
                    error_msg = result.get("message", "Неизвестная ошибка")
                    self.logger.error(f"Ошибка при выполнении действия: {error_msg}")

                    # Если ошибка связана с браузером - пытаемся восстановить
                    if any(keyword in error_msg.lower() for keyword in
                           ["target closed", "page closed", "browser", "connection"]):
                        print(f"\n⚠️  Ошибка браузера: {error_msg}")
                        await self._keepalive_check()

                        # Пытаемся повторить действие один раз
                        if self.browser_started:
                            print("🔄 Повторяю действие...")
                            result = await self.supervisor.supervised_execute(self.executor, current_action)

                # Формируем контекст для агента
                context = self._format_action_result(result, current_action)

                # Для навигационных действий автоматически добавляем текст страницы
                # (если Vision не будет использоваться)
                action_name = current_action.get("action", "")
                needs_page_context = action_name in ["navigate", "search_and_type", "click_by_text", "scroll_down", "scroll_up"]

                if needs_page_context and result.get("status") == "success":
                    # Проверяем: будет ли использоваться Vision?
                    will_use_vision = Config.USE_VISION and self._should_use_vision(current_action, result)

                    if not will_use_vision:
                        # Vision не будет - получаем текст страницы для контекста
                        try:
                            page_result = await self.action_executor.execute({"action": "get_page_text"})
                            if page_result.get("status") == "success" and "text" in page_result:
                                context += f"\nТекст страницы:\n{page_result['text']}\n"
                                if page_result.get("truncated"):
                                    context += f"(Показано {len(page_result['text'])} из {page_result.get('original_length')} символов)\n"
                        except Exception as e:
                            self.logger.warning(f"Не удалось получить текст страницы: {e}")

                # Увеличиваем счётчики
                actions_count += 1
                total_actions += 1

                # Предупреждение о лимите в текущем цикле
                remaining = max_actions_per_cycle - actions_count
                if remaining == 2:
                    context += f"\n\n⚠️ ВНИМАНИЕ: Осталось 2 действия в этом цикле. Если нашёл информацию - сообщи пользователю!"
                elif remaining == 1:
                    context += f"\n\n🚨 КРИТИЧНО: Осталось 1 действие! Сообщи результат пользователю (текстом, БЕЗ JSON)!"

                # Отправляем результат агенту
                print("\n🤖 Агент анализирует результат...")

                try:
                    # Если USE_VISION включен и это действие, которое нужно визуально анализировать
                    if Config.USE_VISION and self._should_use_vision(current_action, result):
                        # ВАЖНО: Ждем полной загрузки страницы перед скриншотом
                        action_name = current_action.get("action", "")

                        # Для навигации и поиска - дополнительное ожидание загрузки контента
                        if action_name in ["navigate", "search_and_type", "click_by_text"]:
                            self.logger.info("Ожидаю загрузки динамического контента...")
                            await asyncio.sleep(3)  # Дополнительное время для AJAX/React/lazy loading

                            # Дополнительно ждем сетевой активности
                            try:
                                await self.browser_tools.page.wait_for_load_state("networkidle", timeout=5000)
                            except Exception as e:
                                self.logger.debug(f"Timeout при ожидании networkidle: {e}")

                        # Делаем скриншот для анализа
                        screenshot_result = await self.browser_tools.take_screenshot()

                        if screenshot_result.get("status") == "success":
                            screenshot_path = screenshot_result.get("path")
                            self.logger.info(f"Используем Vision API с скриншотом: {screenshot_path}")
                            print("📸 Анализирую скриншот страницы...")

                            response = self.agent.chat_with_vision(
                                "Результат выполнения действия. Что дальше?",
                                image_path=screenshot_path,
                                specialized_agent=self.current_specialized_agent
                            )
                        else:
                            # Скриншот не удался - получаем текст страницы как fallback
                            self.logger.warning("Не удалось сделать скриншот, получаю текст страницы")
                            print("⚠️ Скриншот не удался, читаю текст страницы...")

                            try:
                                # get_page_text автоматически ограничивает текст до 800 символов
                                page_result = await self.action_executor.execute({"action": "get_page_text"})
                                if page_result.get("status") == "success" and "text" in page_result:
                                    context += f"\nТекст страницы:\n{page_result['text']}\n"
                                    if page_result.get("truncated"):
                                        context += f"(Текст обрезан: {page_result.get('original_length')} → {len(page_result['text'])} символов)\n"
                            except Exception as e:
                                self.logger.warning(f"Не удалось получить текст страницы: {e}")

                            response = self.agent.chat(
                                "Результат выполнения действия. Что дальше?",
                                context=context,
                                specialized_agent=self.current_specialized_agent
                            )
                    else:
                        # Используем обычный текстовый режим
                        response = self.agent.chat(
                            "Результат выполнения действия. Что дальше?",
                            context=context,
                            specialized_agent=self.current_specialized_agent
                        )
                except Exception as api_error:
                    self.logger.error(f"Ошибка API при анализе результата: {api_error}", exc_info=True)
                    print(f"\n❌ Ошибка API: {api_error}")
                    print("🔄 Пытаюсь переподключиться к API...")

                    # Пересоздаём клиента
                    self.agent = AIAgent()
                    self.agent.add_system_prompt()

                    # Пытаемся ещё раз
                    try:
                        response = self.agent.chat(
                            "Результат выполнения действия. Что дальше?",
                            context=context
                        )
                    except Exception as retry_error:
                        self.logger.error(f"Не удалось восстановить API: {retry_error}", exc_info=True)
                        print(f"❌ Не удалось восстановить API: {retry_error}")
                        print("🤖 Агент: Извините, возникла проблема с подключением.")
                        print("Попробуйте переформулировать запрос.\n")
                        break

                # Проверяем следующее действие
                next_action = self.agent.parse_action(response)

                if next_action:
                    # Есть следующее действие - продолжаем
                    print(f"\n💭 Агент: {response.split('{')[0].strip()}")
                    current_action = next_action
                else:
                    # Агент не дал следующего действия - проверяем нужно ли продолжить поиск

                    # ВСЕГДА проверяем нужно ли автопродолжение (независимо от лимита)
                    should_continue = self._should_continue_search(response)

                    if should_continue and cycle_count < max_cycles - 1:
                        # Агент НЕ дал финального результата - проверяем возможность продолжения

                        if actions_count >= max_actions_per_cycle:
                            # Достигнут лимит цикла - начинаем новый цикл
                            cycle_count += 1
                            actions_count = 0  # Сбрасываем счётчик действий для нового цикла

                            self.logger.info(f"Автопродолжение: цикл {cycle_count + 1}/{max_cycles}, выполнено {total_actions} действий")
                            print(f"\n⏳ Продолжаю поиск (цикл {cycle_count + 1}/{max_cycles})...")
                        else:
                            # Лимит цикла не достигнут, но агент не дал результата - продолжаем в том же цикле
                            self.logger.info(f"Автопродолжение внутри цикла: {actions_count}/{max_actions_per_cycle} действий")
                            print(f"\n⏳ Продолжаю поиск...")

                        # Формируем контекст продолжения
                        continuation_prompt = f"""Выполнено {total_actions} действий за {cycle_count} циклов.
Промежуточный результат: {response[:200] if response else '(нет ответа)'}...

Продолжай поиск. У тебя есть ещё {max_actions_per_cycle - actions_count} действий в этом цикле.
Если найдёшь результат - СРАЗУ сообщи пользователю."""

                        # Получаем следующее действие для продолжения
                        try:
                            continuation_response = self.agent.chat(continuation_prompt)
                            current_action = self.agent.parse_action(continuation_response)

                            if not current_action:
                                # Агент не дал действия даже после запроса - завершаем
                                print(f"\n🤖 Агент: {response if response else 'Извините, не удалось найти результат.'}\n")
                                current_action = None
                        except Exception as e:
                            self.logger.error(f"Ошибка при автопродолжении: {e}")
                            print(f"\n🤖 Агент: {response if response else 'Произошла ошибка при поиске.'}\n")
                            current_action = None
                    else:
                        # Агент дал финальный результат ИЛИ исчерпаны циклы - выводим ответ
                        print(f"\n🤖 Агент: {response}\n")
                        current_action = None

            except KeyboardInterrupt:
                print("\n\n⚠️  Действие прервано пользователем")
                self.logger.info("Действие прервано пользователем")
                break

            except Exception as e:
                self.logger.error(f"Критическая ошибка при выполнении действия: {e}", exc_info=True)
                print(f"\n❌ Критическая ошибка: {e}")
                print("🤖 Агент: Произошла ошибка. Попробуйте ещё раз.\n")
                break

        # Финальная проверка - исчерпаны ли все циклы
        if cycle_count >= max_cycles:
            self.logger.warning(f"Исчерпаны все циклы: {cycle_count} циклов, {total_actions} действий")
            print(f"\n⚠️ Выполнено {total_actions} действий за {cycle_count} циклов.")
            print("🤖 Агент: К сожалению, не удалось найти точный ответ. Попробуйте переформулировать запрос.\n")

    def _should_use_vision(self, action: dict, result: dict) -> bool:
        """
        Определить, нужно ли использовать Vision API для анализа результата

        Vision ДЕЙСТВИТЕЛЬНО полезен только для:
        - Модальных окон (конструктор блюд, попапы)
        - Интерактивных элементов (кнопки, чекбоксы, селекторы)
        - Случаев когда текст не дает полной картины

        Vision ИЗБЫТОЧЕН для:
        - Обычной навигации (текст страницы достаточен)
        - Чтения меню и списков (текст лучше и быстрее)
        - Поиска (результаты в тексте)
        - Скролла (текст показывает контент)

        Args:
            action: выполненное действие
            result: результат действия

        Returns:
            True если нужен Vision API
        """
        # Если действие завершилось ошибкой - Vision не нужен
        if result.get("status") != "success":
            return False

        action_name = action.get("action", "")

        # Проверяем URL - для погоды Vision НУЖЕН
        url = result.get("url", "")
        if "pogoda" in url.lower() or "weather" in url.lower():
            return True  # Погода - большие цифры, иконки, визуальная инфо

        # Vision только для ИНТЕРАКТИВНЫХ действий и модальных окон
        vision_actions = [
            "wait_for_modal",              # Модальное окно появилось - нужно видеть
            "get_modal_text",              # Читаем модалку - может быть интерактивной
            "get_dish_customization_options",  # Конструктор - интерактивные элементы
            "toggle_option",               # Переключили опцию - нужно видеть результат
            "adjust_quantity",             # Изменили количество - проверить визуально
            "select_size",                 # Выбрали размер - увидеть изменения
        ]

        return action_name in vision_actions

    def _format_action_result(self, result: dict, action: dict) -> str:
        """Форматировать результат действия для агента"""
        action_name = action.get("action", "unknown")
        status = result.get("status", "unknown")

        context = f"Действие: {action_name}\n"
        context += f"Статус: {status}\n"

        if status == "success":
            # Добавляем полезную информацию из результата
            if "text" in result:
                # Ограничиваем текст страницы (экономия токенов)
                # get_page_text уже ограничен до 800 символов в action_executor
                # Если Vision включен — дополнительно обрезаем до 500 (скриншоты важнее текста)
                max_text_length = 500 if Config.USE_VISION else 1000
                text = result["text"][:max_text_length]

                # Показываем информацию об обрезке
                original_len = result.get("original_length", len(result["text"]))
                if len(result["text"]) > max_text_length or result.get("truncated"):
                    text += f"\n... (показано {len(text)} из {original_len} символов)"

                context += f"\nТекст страницы:\n{text}\n"

            if "url" in result:
                context += f"URL: {result['url']}\n"

            if "title" in result:
                context += f"Title: {result['title']}\n"

            if "message" in result:
                context += f"Сообщение: {result['message']}\n"

        else:
            # Ошибка
            context += f"Ошибка: {result.get('message', 'Неизвестная ошибка')}\n"

        return context


    def _setup_logging(self):
        """Настроить систему логирования с ротацией"""
        # Используем новую систему логирования с автоматической ротацией
        LogSetup.setup_logging(log_dir="logs")
        self.logger = logging.getLogger(__name__)

    def _is_exit_command(self, user_input: str) -> bool:
        """
        Проверить, является ли ввод пользователя командой выхода

        Использует word boundaries для корректного распознавания прощаний
        в составе фраз типа "Спасибо. Пока" и избегания ложных срабатываний
        на слова типа "Покажи" (содержит "пока")

        Args:
            user_input: ввод пользователя

        Returns:
            True если это команда выхода, False иначе
        """
        text = user_input.lower().strip()

        # Однозначные команды выхода (английские и альтернативные русские)
        simple_exits = r'\b(exit|quit|выход|прощай|досвидания|довстречи|до\s*свидания|до\s*встречи)\b'
        if re.search(simple_exits, text, re.IGNORECASE):
            return True

        # "Пока" - только если НЕ в начале предложения с последующим "не"
        # Это отфильтрует "Пока не голоден", но оставит "Спасибо. Пока"
        if re.search(r'\bпока\b', text):
            # Проверяем: если "пока" в начале и за ним идёт "не" - это союз, не прощание
            if not re.match(r'^пока\s+не\b', text):
                return True

        return False

    def _should_continue_search(self, response: str) -> bool:
        """
        Определить, нужно ли агенту продолжать поиск (автоматическое продолжение)

        Агент должен продолжить поиск если:
        - Ответ пустой или очень короткий
        - Ответ содержит JSON (технический ответ, не пользовательский)
        - Ответ содержит промежуточные статусы ("ищу", "продолжаю", "не нашёл")

        Агент должен завершить если:
        - Ответ содержит конкретную рекомендацию или результат
        - Ответ содержит цены, названия блюд
        - Ответ содержит финальный негативный результат ("к сожалению, нет")

        Args:
            response: ответ агента

        Returns:
            True если нужно продолжить поиск, False если агент дал финальный ответ
        """
        response = response.strip()

        # Пустой или очень короткий ответ - продолжаем
        if not response or len(response) < 20:
            return True

        # JSON ответ (технический) - продолжаем
        if response.startswith("{") and response.endswith("}"):
            return True

        response_lower = response.lower()

        # Промежуточные фразы - продолжаем поиск
        intermediate_phrases = [
            "продолжаю", "ищу", "прокручиваю", "не нашёл",
            "не нашлось", "пока не вижу", "еще ищу", "продолжаю искать"
        ]
        if any(phrase in response_lower for phrase in intermediate_phrases):
            return True

        # Финальные фразы - завершаем
        final_phrases = [
            "рекомендую", "предлагаю", "нашёл", "есть вариант",
            "подойдёт", "к сожалению", "увы", "не могу найти",
            "вот что", "можешь выбрать", "попробуй",
            # Погода
            "температура", "градус", "осадк", "прогноз", "погода",
            "ощущается", "ветер", "влажность"
        ]
        if any(phrase in response_lower for phrase in final_phrases):
            return False

        # Если содержит цену или градусы - это конкретный результат
        if "₽" in response or "руб" in response_lower or "°" in response:
            return False

        # По умолчанию - завершаем (на всякий случай не зацикливаем)
        return False

    async def _get_user_input_with_timeout(self) -> Optional[str]:
        """
        Получить ввод пользователя с таймаутом и keepalive проверками

        Returns:
            str: ввод пользователя
            None: если таймаут истёк
        """
        timeout_seconds = Config.USER_INPUT_TIMEOUT
        keepalive_interval = Config.KEEPALIVE_INTERVAL

        start_time = time.time()
        last_keepalive = start_time

        # Запускаем input в отдельном потоке
        input_task = asyncio.create_task(
            asyncio.to_thread(input, "👤 Вы: ")
        )

        while not input_task.done():
            current_time = time.time()
            elapsed = current_time - start_time

            # Проверка таймаута
            if elapsed > timeout_seconds:
                input_task.cancel()
                print(f"\n⏱️  Таймаут ожидания ввода ({timeout_seconds // 60} минут).")
                print("Вы ещё здесь? (У вас есть ещё 1 минута)")
                self.logger.warning(f"Таймаут ожидания ввода: {elapsed:.0f} секунд")

                # Даём дополнительное время (grace period)
                try:
                    result = await asyncio.wait_for(
                        asyncio.to_thread(input, "👤 Вы: "),
                        timeout=Config.USER_INPUT_GRACE_PERIOD
                    )
                    self.logger.info("Пользователь вернулся после таймаута")
                    return result
                except asyncio.TimeoutError:
                    print("\n⏱️  Второй таймаут. Завершаю сессию для экономии ресурсов.")
                    self.logger.warning("Второй таймаут - завершение сессии")
                    return None

            # Keepalive - проверяем состояние браузера
            if Config.BROWSER_CHECK_ENABLED and (current_time - last_keepalive > keepalive_interval):
                await self._keepalive_check()
                last_keepalive = current_time

            # Маленькая пауза чтобы не нагружать CPU
            await asyncio.sleep(0.5)

        # Получаем результат
        return await input_task

    async def _keepalive_check(self):
        """
        Проверить состояние браузера и переподключиться при необходимости
        """
        if not self.browser_started:
            return

        try:
            # Простая проверка - получаем URL текущей страницы
            if self.browser_tools.page:
                # page.url это property, не coroutine, поэтому без await
                url = self.browser_tools.page.url
                # Браузер живой
                self.logger.debug("Keepalive: браузер активен")
                return
        except (asyncio.TimeoutError, Exception) as e:
            # Браузер упал
            self.logger.error(f"Браузер недоступен: {e}")
            print(f"\n⚠️  Браузер недоступен: {e}")
            print("🔄 Переподключаюсь к браузеру...")

            try:
                # Закрываем старое соединение (если оно есть)
                try:
                    await asyncio.wait_for(
                        self.browser_tools.close_browser(),
                        timeout=3.0
                    )
                except:
                    pass

                # Создаём новое
                await self.browser_tools.start_browser(
                    headless=Config.BROWSER_HEADLESS
                )
                print("✅ Браузер переподключён\n")
                self.logger.info("Браузер успешно переподключён")

            except Exception as reconnect_error:
                self.logger.error(f"Не удалось переподключить браузер: {reconnect_error}")
                print(f"❌ Не удалось переподключить браузер: {reconnect_error}")
                print("Попробуйте перезапустить программу\n")
                self.browser_started = False

    def _print_token_stats(self):
        """Выводит статистику использования токенов в консоль"""
        try:
            stats = self.agent.get_token_usage_stats()

            print("\n" + "="*60)
            print("📊 СТАТИСТИКА ИСПОЛЬЗОВАНИЯ ТОКЕНОВ")
            print("="*60)
            print(f"  🤖 Модель: {stats['model']}")
            print(f"  📏 Лимит модели: {stats['model_limit']} токенов")
            print(f"  ✅ Безопасный лимит: {stats['safe_limit']} токенов")
            print(f"  📊 Использовано: {stats['used_tokens']} токенов ({stats['usage_percent']:.1f}%)")
            print(f"  💾 Доступно: {stats['available_tokens']} токенов")
            print("-"*60)
            print(f"  📋 Уровень контекста: {stats['context_level'].upper()}")
            print(f"  📝 Уровень промпта: {stats['prompt_level'].upper()}")
            print(f"  🎯 Тип задачи: {stats['task_type'] or 'Общая'}")
            print(f"  💰 Экономия KB: {stats['kb_savings_percent']}%")
            print("="*60 + "\n")

        except Exception as e:
            self.logger.error(f"Ошибка при выводе статистики: {e}")

    async def _update_working_memory_from_response(
        self,
        user_input: str,
        agent_response: str,
        action: Optional[dict] = None
    ):
        """
        Автоматически обновляет working_memory на основе ответа агента

        Анализирует ответ и определяет:
        - Текущую задачу (что делает агент)
        - Где находится (на какой странице)
        - Какие варианты показал (для выбора пользователем)
        - Последнее действие

        Args:
            user_input: Запрос пользователя
            agent_response: Ответ агента
            action: Действие, которое собирается выполнить агент
        """
        if not self.knowledge_base:
            return

        import re

        # 1. Определяем текущую задачу
        current_task = None
        if action:
            reasoning = action.get("reasoning", "")
            action_name = action.get("action", "")

            # Извлекаем задачу из reasoning или action
            if "заказ" in reasoning.lower() or "ищу" in reasoning.lower():
                # Пытаемся извлечь что именно заказываем
                match = re.search(r'(заказ\w*|ищу|найти)\s+([^.]+)', reasoning, re.IGNORECASE)
                if match:
                    current_task = match.group(0)
            elif action_name == "navigate":
                url = action.get("params", {}).get("url", "")
                if "dodo" in url.lower():
                    current_task = f"Заказ из Додопиццы"

        # 2. Определяем текущую страницу
        current_page = None
        if action:
            action_name = action.get("action", "")
            if action_name == "navigate":
                url = action.get("params", {}).get("url", "")
                if url:
                    # Извлекаем домен
                    domain_match = re.search(r'https?://([^/]+)', url)
                    if domain_match:
                        current_page = f"переход на {domain_match.group(1)}"
            elif action_name in ["search_and_type", "click_by_text"]:
                current_page = "на странице поиска/результатов"

        # 3. Определяем показанные варианты
        shown_options = []
        # Ищем нумерованные списки в ответе: "1. ...", "2. ..."
        list_matches = re.findall(r'^\s*\d+\.\s*([^\n]+)', agent_response, re.MULTILINE)
        if list_matches and len(list_matches) >= 2:
            # Если найдено 2+ вариантов - это показ вариантов
            shown_options = list_matches[:5]  # Максимум 5

        # 4. Определяем последнее действие
        last_action = None
        if action:
            action_name = action.get("action", "")
            if shown_options:
                last_action = f"показал {len(shown_options)} вариантов"
            elif action_name == "navigate":
                last_action = "переход на новую страницу"
            elif action_name == "search_and_type":
                last_action = "поиск"
            elif action_name == "click_by_text":
                last_action = "клик по элементу"
            elif action_name == "get_page_text":
                last_action = "чтение страницы"

        # Обновляем working memory только если есть что обновлять
        if any([current_task, current_page, shown_options, last_action]):
            self.knowledge_base.set_working_context(
                current_task=current_task,
                current_page=current_page,
                shown_options=shown_options if shown_options else None,
                last_action=last_action
            )
            self.logger.debug(
                f"Working memory обновлена: task={current_task}, "
                f"page={current_page}, options={len(shown_options) if shown_options else 0}"
            )

    async def _cleanup(self):
        """Очистка ресурсов"""
        # Сохраняем статистику supervisor
        if self.supervisor:
            self.supervisor.save_session_summary()

            # Выводим статистику
            stats = self.supervisor.get_statistics()
            if stats["total_errors"] > 0:
                self.logger.info(
                    f"Session stats: {stats['total_errors']} errors "
                    f"({stats['runtime_errors']} runtime, {stats['structured_errors']} structured)"
                )

        if self.browser_started:
            print("\n🔒 Закрываю браузер...")
            await self.browser_tools.close_browser()
            print("✓ Браузер закрыт")
        self.logger.info("Сессия завершена")
