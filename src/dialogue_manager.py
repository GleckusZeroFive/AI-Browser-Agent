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
from src.tools.browser_tools import BrowserTools
from src.config import Config

class DialogueManager:
    """Менеджер диалога пользователя с AI агентом"""

    def __init__(self):
        self.agent = AIAgent()
        self.browser_tools = BrowserTools()
        self.executor = ActionExecutor(self.browser_tools)
        self.browser_started = False

        # Отслеживание ограничений пользователя (аллергии, предпочтения)
        self.user_restrictions = {
            "allergies": [],  # Список аллергенов ["морепродукты", "орехи"]
            "dislikes": [],   # Список нежелательных продуктов ["помидоры", "грибы"]
            "preferences": [] # Предпочтения ["острое", "без мяса"]
        }

        # Настройка логирования
        self._setup_logging()

    async def start(self):
        """Запустить диалоговую систему"""
        print("=" * 70)
        print("🤖 AI BROWSER AGENT")
        print("=" * 70)

        # Инициализируем агента
        self.agent.add_system_prompt()

        # Запускаем браузер
        print("\n🌐 Запускаю браузер...")
        await self.browser_tools.start_browser(headless=Config.BROWSER_HEADLESS)
        self.browser_started = True
        print("✓ Браузер готов\n")

        # ПРИВЕТСТВИЕ ОТ АГЕНТА
        print("🤖 Агент: Привет! Я автономный AI-агент для работы с браузером.")
        print("   Могу помочь с:")
        print("   • Заказом еды")
        print("   • Поиском вакансий")
        print("   • Покупками онлайн")
        print("   • И другими задачами в интернете")
        print("\n   Какую задачу выполнить?\n")
        print("(Напиши задачу или 'exit' для выхода)\n")

        # Главный цикл диалога
        try:
            await self._dialogue_loop()
        finally:
            await self._cleanup()

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

                # Отправляем в AI агента
                print("\n🤖 Агент думает...")

                try:
                    response = self.agent.chat(user_input)
                    self.logger.info(f"Агент ответил: {response[:100]}...")
                except Exception as api_error:
                    self.logger.error(f"Ошибка API: {api_error}", exc_info=True)
                    print(f"\n❌ Ошибка связи с API: {api_error}")
                    print("Попробуйте ещё раз.\n")
                    continue

                # ЛОГИРОВАНИЕ: Сохраняем полный ответ агента
                with open("logs/agent_responses.log", "a", encoding="utf-8") as f:
                    f.write(f"\n{'='*60}\n")
                    f.write(f"USER: {user_input}\n")
                    f.write(f"AGENT RESPONSE:\n{response}\n")

                # Проверяем, это диалог или действие?
                action = self.agent.parse_action(response)

                # ЛОГИРОВАНИЕ: Результат парсинга
                with open("logs/agent_responses.log", "a", encoding="utf-8") as f:
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
                        print(f"\n💭 Агент: {response.split('{')[0].strip()}")

                        await self._execute_action_with_followup(action)

                else:
                    # Режим диалога - просто отвечаем
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

                # Выполняем действие
                self.logger.info(f"Выполняю действие: {current_action.get('action')}")
                result = await self.executor.execute(current_action)

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
                            result = await self.executor.execute(current_action)

                # Формируем контекст для агента
                context = self._format_action_result(result, current_action)

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
                    response = self.agent.chat(
                        "Результат выполнения действия. Что дальше?",
                        context=context
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

    def _format_action_result(self, result: dict, action: dict) -> str:
        """Форматировать результат действия для агента"""
        action_name = action.get("action", "unknown")
        status = result.get("status", "unknown")

        context = f"Действие: {action_name}\n"
        context += f"Статус: {status}\n"

        if status == "success":
            # Добавляем полезную информацию из результата
            if "text" in result:
                # Ограничиваем текст страницы
                text = result["text"][:3000]  # первые 3000 символов
                context += f"\nТекст страницы (начало):\n{text}\n"

            if "url" in result:
                context += f"URL: {result['url']}\n"

            if "title" in result:
                context += f"Title: {result['title']}\n"

            if "message" in result:
                context += f"Сообщение: {result['message']}\n"

        else:
            # Ошибка
            context += f"Ошибка: {result.get('message', 'Неизвестная ошибка')}\n"

        # Добавляем ограничения пользователя в контекст
        restrictions_text = self._format_user_restrictions()
        if restrictions_text:
            context += f"\n{restrictions_text}"

        return context

    def _format_user_restrictions(self) -> str:
        """Форматировать ограничения пользователя для контекста агента"""
        parts = []

        if self.user_restrictions["allergies"]:
            allergies = ", ".join(self.user_restrictions["allergies"])
            parts.append(f"🚨 АЛЛЕРГИИ: {allergies}")

        if self.user_restrictions["dislikes"]:
            dislikes = ", ".join(self.user_restrictions["dislikes"])
            parts.append(f"❌ НЕ ЕСТ: {dislikes}")

        if self.user_restrictions["preferences"]:
            prefs = ", ".join(self.user_restrictions["preferences"])
            parts.append(f"✅ ПРЕДПОЧИТАЕТ: {prefs}")

        if parts:
            return "\n⚠️ ОГРАНИЧЕНИЯ ПОЛЬЗОВАТЕЛЯ:\n" + "\n".join(parts)

        return ""

    def _setup_logging(self):
        """Настроить систему логирования"""
        import os
        os.makedirs("logs", exist_ok=True)

        # Настройка основного логгера
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler('logs/dialogue_manager.log', encoding='utf-8')
            ]
        )

        self.logger = logging.getLogger(__name__)

        # Отдельный файл для ошибок
        error_handler = logging.FileHandler('logs/errors.log', encoding='utf-8')
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(
            logging.Formatter('%(asctime)s [ERROR] %(message)s\n')
        )
        self.logger.addHandler(error_handler)

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
            "вот что", "можешь выбрать", "попробуй"
        ]
        if any(phrase in response_lower for phrase in final_phrases):
            return False

        # Если содержит цену - это конкретный результат
        if "₽" in response or "руб" in response_lower:
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

    async def _cleanup(self):
        """Очистка ресурсов"""
        if self.browser_started:
            print("\n🔒 Закрываю браузер...")
            await self.browser_tools.close_browser()
            print("✓ Браузер закрыт")
        self.logger.info("Сессия завершена")
