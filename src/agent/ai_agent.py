import json
import time
import logging
from typing import Dict, Any, List, Optional
from openai import OpenAI
from src.config import Config, ModelType

class AIAgent:
    """Универсальный AI агент для автоматизации браузера с умным выбором модели"""

    def __init__(self):
        self.client = OpenAI(
            api_key=Config.get_api_key(),
            base_url=Config.get_base_url()
        )
        self.current_model = Config.DEFAULT_MODEL
        self.conversation_history: List[Dict[str, str]] = []
        self.current_plan: List[str] = []
        self.last_request_time = 0
        self.rate_limit_count = 0  # Счётчик rate limit ошибок
        self.logger = logging.getLogger(__name__)

    def add_system_prompt(self):
        """Добавить системный промпт"""
        system_prompt = """Ты - автономный AI-агент для управления веб-браузером. Ты можешь решать ЛЮБЫЕ задачи в интернете.

═══════════════════════════════════════════════════════════════
🎯 ТВОЯ ЦЕЛЬ
═══════════════════════════════════════════════════════════════

Выполнять сложные многошаговые задачи в браузере ПОЛНОСТЬЮ АВТОНОМНО:
- Заказ еды на любом сайте
- Поиск вакансий
- Удаление спама из почты
- Бронирование билетов
- Покупки в интернет-магазинах
- И любые другие задачи

🤖 АРХИТЕКТУРА СПЕЦИАЛИЗИРОВАННЫХ АГЕНТОВ
Система автоматически активирует специализированных агентов для:
• EmailAgent - работа с почтой (Yandex, Gmail)
• ShoppingAgent - заказ еды и покупки
• JobSearchAgent - поиск работы на hh.ru

Когда пользователь начинает специализированную задачу, система переключает
тебя на специализированного агента с экспертным промптом для этой области.

═══════════════════════════════════════════════════════════════
🛠️ ДОСТУПНЫЕ ДЕЙСТВИЯ
═══════════════════════════════════════════════════════════════

НАВИГАЦИЯ:
- navigate(url) - открыть любую страницу
- scroll_down(pixels) - прокрутить вниз (по умолчанию 500)
- scroll_up(pixels) - прокрутить вверх

ЧТЕНИЕ СТРАНИЦЫ:
- get_page_text() - получить весь текст страницы
- find_text(search_text) - найти конкретный текст (Ctrl+F)
- get_modal_text() - получить текст модального окна/попапа

ВЗАИМОДЕЙСТВИЕ:
- click_by_text(text) - кликнуть по элементу с текстом
- type_text(selector, text) - ввести текст в поле
- press_key(key) - нажать клавишу (Enter, Escape, Tab)

МОДАЛЬНЫЕ ОКНА:
- wait_for_modal(timeout) - ждать появления модального окна
- close_modal() - закрыть модальное окно (Escape)

ФОРМАТ КОМАНДЫ (JSON):
{"action": "navigate", "params": {"url": "https://example.com"}, "reasoning": "Открываю сайт для начала работы"}

═══════════════════════════════════════════════════════════════
🧠 ПАТТЕРН ПЛАНИРОВАНИЯ (ОБЯЗАТЕЛЬНО!)
═══════════════════════════════════════════════════════════════

Перед началом работы ВСЕГДА составь план:

1. АНАЛИЗ ЗАДАЧИ
   - Что конкретно нужно сделать?
   - Какой сайт/сервис использовать?
   - Какая информация нужна от пользователя?

2. ПЛАН ДЕЙСТВИЙ (разбей на шаги)
   Пример для "закажи пиццу":
   - Шаг 1: Уточнить количество людей и предпочтения
   - Шаг 2: Найти сайт доставки еды через поиск
   - Шаг 3: Открыть сайт и изучить меню
   - Шаг 4: Выбрать подходящие блюда
   - Шаг 5: Добавить в корзину
   - Шаг 6: Оформить заказ

3. ВЫПОЛНЕНИЕ
   - Выполняй шаги последовательно
   - После каждого шага проверяй результат
   - Если что-то не работает - адаптируй план

4. РЕФЛЕКСИЯ
   - Получилось ли выполнить шаг?
   - Нужно ли изменить подход?
   - Что делать дальше?

═══════════════════════════════════════════════════════════════
🔍 КАК НАХОДИТЬ САЙТЫ (БЕЗ ХАРДКОДА!)
═══════════════════════════════════════════════════════════════

❌ НЕЛЬЗЯ: использовать заготовленные URL
❌ НЕЛЬЗЯ: знать заранее структуру сайта

✅ НУЖНО: находить сайты через поиск
✅ НУЖНО: исследовать страницу через get_page_text()
✅ НУЖНО: адаптироваться к любому сайту

Пример правильного подхода:
1. Пользователь: "Закажи пиццу"
2. Ты: "В каком городе?"
3. Пользователь: "Красноярск"
4. Ты: navigate("https://www.google.com/search?q=заказать+пиццу+Красноярск")
5. Изучаешь результаты поиска
6. Выбираешь подходящий сайт
7. Исследуешь его структуру через get_page_text()

═══════════════════════════════════════════════════════════════
🚨 КРИТИЧЕСКИЕ ПРАВИЛА
═══════════════════════════════════════════════════════════════

1. НЕ ГАЛЛЮЦИНИРУЙ
   - Кликай ТОЛЬКО на то, что видел в get_page_text()
   - Если элемента нет на странице - ищи другой способ
   - После ошибки клика - пробуй альтернативу

2. РАБОТАЙ С РЕАЛЬНЫМИ ДАННЫМИ
   - Сначала get_page_text() → потом действия
   - Читай что РЕАЛЬНО есть на странице
   - Не придумывай названия кнопок и ссылок

3. АДАПТИРУЙСЯ
   - Каждый сайт уникален
   - Исследуй структуру перед действиями
   - Если один способ не работает - пробуй другой

4. УТОЧНЯЙ ДЕТАЛИ
   - Спрашивай важную информацию (город, предпочтения, ограничения)
   - Не делай предположений
   - Лучше спросить, чем ошибиться

5. БЕЗОПАСНОСТЬ (SECURITY LAYER)
   - ОСТАНАВЛИВАЙСЯ перед деструктивными действиями
   - НЕ нажимай "Оплатить" без явного запроса пользователя
   - НЕ удаляй данные без подтверждения
   - Система автоматически запросит подтверждение для опасных действий
   - Твоя задача - дойти до точки подтверждения, но не выполнять финальное действие

═══════════════════════════════════════════════════════════════
💬 ФОРМАТ ОБЩЕНИЯ
═══════════════════════════════════════════════════════════════

ДИАЛОГ (нужна информация) = ТЕКСТ БЕЗ JSON
Примеры:
- "В каком городе вы находитесь?"
- "Сколько человек будет?"
- "Есть ли у вас аллергия или предпочтения?"
- "Нашёл несколько вариантов: ..."

ДЕЙСТВИЕ (выполняю работу) = JSON
Примеры:
- {"action": "navigate", "params": {"url": "..."}, "reasoning": "..."}
- {"action": "click_by_text", "params": {"text": "..."}, "reasoning": "..."}
- {"action": "get_page_text", "params": {}, "reasoning": "..."}

ВАЖНО:
- Если нужно спросить пользователя → ТОЛЬКО текст, БЕЗ JSON
- Если выполняешь действие → ТОЛЬКО JSON
- НЕ смешивай в одном сообщении

═══════════════════════════════════════════════════════════════
📋 ПРИМЕРЫ ЗАДАЧ
═══════════════════════════════════════════════════════════════

ЗАКАЗ ЕДЫ:
1. Уточни город, количество людей, предпочтения/аллергии
2. Найди сайт доставки через поиск
3. Изучи меню через get_page_text()
4. Подбери блюда по критериям
5. Сообщи пользователю варианты

ПОИСК ВАКАНСИЙ:
1. Уточни специальность, город, требования
2. Найди сайт с вакансиями (hh.ru, superjob и т.д.)
3. Введи параметры поиска
4. Изучи результаты
5. Покажи подходящие варианты

УДАЛЕНИЕ СПАМА:
1. Уточни какую почту использует пользователь
2. Перейди на сайт почты
3. Изучи структуру (где входящие, как отмечать)
4. Найди спам-письма
5. Удали их

═══════════════════════════════════════════════════════════════
🔄 АВТОМАТИЧЕСКОЕ ПРОДОЛЖЕНИЕ
═══════════════════════════════════════════════════════════════

Система даёт тебе до 30 действий (3 цикла по 10).
Если не нашёл результат - продолжай искать молча.
НЕ сообщай пользователю технические детали поиска.
Сообщай ТОЛЬКО финальный результат.

Ты готов к работе. Жди задачу от пользователя."""

        self.conversation_history.append({
            "role": "system",
            "content": system_prompt
        })

    def _select_model_for_request(self, message: str, context: str = None) -> str:
        """Выбрать подходящую модель для запроса"""
        # Если много rate limit ошибок - используем быструю модель
        if self.rate_limit_count >= 2:
            return Config.MODELS[ModelType.FAST]

        # Для анализа больших страниц используем быструю модель
        if context and len(context) > 2000:
            return Config.MODELS[ModelType.FAST]

        # Для первого запроса и планирования - умная модель
        if len(self.conversation_history) <= 2:
            return Config.MODELS[ModelType.FAST]  # Начинаем с быстрой

        return self.current_model

    def _enforce_rate_limit(self):
        """Соблюдать минимальный интервал между запросами"""
        elapsed = time.time() - self.last_request_time
        if elapsed < Config.MIN_REQUEST_INTERVAL:
            time.sleep(Config.MIN_REQUEST_INTERVAL - elapsed)
        self.last_request_time = time.time()

    def chat(self, user_message: str, context: Optional[str] = None) -> str:
        """Отправить сообщение агенту с умным выбором модели и fallback"""

        # Добавляем контекст если есть (например, текст страницы)
        if context:
            full_message = f"{user_message}\n\nКонтекст:\n{context}"
        else:
            full_message = user_message

        self.conversation_history.append({
            "role": "user",
            "content": full_message
        })

        # Выбираем модель для запроса
        model_to_use = self._select_model_for_request(user_message, context)

        # Список моделей для fallback
        models_to_try = [model_to_use] + [m for m in Config.FALLBACK_MODELS if m != model_to_use]

        for model in models_to_try:
            try:
                # Соблюдаем rate limit
                self._enforce_rate_limit()

                self.logger.info(f"Запрос к модели: {model}")

                response = self.client.chat.completions.create(
                    model=model,
                    messages=self.conversation_history,
                    temperature=Config.TEMPERATURE,
                    max_tokens=Config.MAX_TOKENS,
                )

                assistant_message = response.choices[0].message.content

                self.conversation_history.append({
                    "role": "assistant",
                    "content": assistant_message
                })

                # Успешный запрос - сбрасываем счётчик rate limit
                self.rate_limit_count = 0
                self.current_model = model

                return assistant_message

            except Exception as e:
                error_str = str(e)
                error_type = type(e).__name__

                # Rate limit - пробуем следующую модель
                if "429" in error_str or "rate limit" in error_str.lower():
                    self.rate_limit_count += 1
                    remaining_models = [m for m in models_to_try if m != model and models_to_try.index(m) > models_to_try.index(model)]
                    if remaining_models:
                        self.logger.warning(f"⚠️ Rate limit для {model}, переключаюсь на {remaining_models[0]}")
                        print(f"⚠️ Rate limit достигнут, переключаюсь на другую модель...")
                    else:
                        self.logger.warning(f"⚠️ Rate limit для {model}, это последняя модель")
                    time.sleep(Config.RATE_LIMIT_RETRY_DELAY)
                    continue

                # Модель недоступна - пробуем следующую
                if "404" in error_str or "not found" in error_str.lower():
                    self.logger.warning(f"Модель {model} недоступна, пробую следующую")
                    continue

                # API key проблемы
                if "401" in error_str or "unauthorized" in error_str.lower() or "invalid api key" in error_str.lower():
                    self.logger.error(f"Ошибка авторизации API: {e}")
                    return (
                        "❌ Ошибка авторизации API (неверный API ключ).\n\n"
                        "Проверьте ваш GROQ_API_KEY в файле .env:\n"
                        "1. Убедитесь что ключ правильный\n"
                        "2. Проверьте что ключ активен на https://console.groq.com\n"
                        "3. Попробуйте создать новый ключ\n\n"
                        f"Детали ошибки: {error_str}"
                    )

                # Сетевые ошибки
                if "connection" in error_str.lower() or "network" in error_str.lower() or "timeout" in error_str.lower():
                    self.logger.error(f"Ошибка сети: {e}")
                    return (
                        f"❌ Ошибка подключения к API ({error_type}).\n\n"
                        "Возможные причины:\n"
                        "- Отсутствует интернет-соединение\n"
                        "- API сервис временно недоступен\n"
                        "- Проблемы с сетью\n\n"
                        "Попробуйте:\n"
                        "1. Проверить интернет-соединение\n"
                        "2. Повторить запрос через несколько секунд\n\n"
                        f"Детали: {error_str}"
                    )

                # Другая ошибка - возвращаем с подробностями
                self.logger.error(f"Ошибка API ({error_type}): {e}", exc_info=True)
                return (
                    f"❌ Ошибка API ({error_type}).\n"
                    f"Детали: {error_str}\n\n"
                    "Попробуйте повторить запрос или обратитесь к документации API."
                )

        # Все модели недоступны
        self.logger.error("Все модели недоступны после нескольких попыток")
        return (
            "❌ Все доступные модели недоступны или достигнут rate limit.\n\n"
            "Возможные причины:\n"
            "- Достигнут лимит запросов на все модели\n"
            "- Сервис Groq временно недоступен\n"
            "- Проблемы с API ключом\n\n"
            "Попробуйте:\n"
            "1. Подождать несколько минут и повторить\n"
            "2. Проверить статус на https://status.groq.com\n"
            "3. Проверить лимиты вашего API ключа на https://console.groq.com"
        )

    def parse_action(self, response: str) -> Optional[Dict[str, Any]]:
        """Попытаться распарсить JSON действие из ответа"""
        try:
            # Ищем JSON в ответе
            if "{" in response and "}" in response:
                start = response.find("{")
                end = response.rfind("}") + 1
                json_str = response[start:end]
                action = json.loads(json_str)

                # Проверяем что это действие, а не что-то другое
                if "action" in action:
                    return action
            return None
        except:
            return None

    def reset_conversation(self):
        """Сбросить историю разговора"""
        self.conversation_history = []
        self.current_plan = []
        self.add_system_prompt()
