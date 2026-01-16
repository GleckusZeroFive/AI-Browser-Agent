"""
Специализированные агенты для разных типов задач

Каждый агент оптимизирован для конкретного домена с кастомным промптом и моделью.
Это реализация паттерна Sub-agent architecture из требований задания.
"""
from typing import Dict, List, Optional
from enum import Enum
from src.config import Config
from src.prompts.prompt_manager import PromptManager, PromptLevel
import logging

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Типы задач для автоматического выбора агента"""
    SHOPPING = "shopping"    # Додопицца
    GENERAL = "general"      # Погода и прочее


class SpecializedAgent:
    """Базовый класс для специализированных агентов"""

    def __init__(self, agent_name: str, model: str):
        """
        Args:
            agent_name: Имя агента для загрузки промпта ("shopping", "email", "job_search")
            model: Название модели для агента
        """
        self.agent_name = agent_name
        self.model = model
        self.prompt_manager = PromptManager()
        self._cached_prompt: Optional[str] = None
        self._cached_level: Optional[PromptLevel] = None

    def get_system_prompt(self, level: PromptLevel = PromptLevel.COMPACT) -> str:
        """
        Получает системный промпт для указанного уровня

        Args:
            level: Уровень детализации промпта

        Returns:
            Системный промпт
        """
        # Кешируем промпт если уровень не изменился
        if self._cached_prompt and self._cached_level == level:
            logger.debug(f"Используется кешированный промпт для {self.agent_name} ({level.value})")
            return self._cached_prompt

        # Загружаем новый промпт
        try:
            prompt = self.prompt_manager.load_prompt(self.agent_name, level)
        except FileNotFoundError as e:
            logger.error(f"Ошибка загрузки промпта: {e}")
            # Fallback на старые inline промпты если файлы не найдены
            raise

        # Кешируем
        self._cached_prompt = prompt
        self._cached_level = level

        logger.info(f"Загружен промпт для {self.agent_name}: level={level.value}, tokens={self.prompt_manager.estimate_prompt_tokens(prompt)}")

        return prompt

    def get_model(self) -> str:
        """Получить модель агента"""
        return self.model


# EmailAgent удален - поддерживаем только погоду и пиццу


class ShoppingAgent(SpecializedAgent):
    """
    Агент для заказа пиццы в Додопицце

    Специализация:
    - Заказ пиццы ТОЛЬКО в Dodopizza (dodopizza.ru/[город])
    - Работа с конструктором блюд
    - Кастомизация пиццы (размер, добавки, убрать ингредиенты)

    Модель: meta-llama/llama-4-scout-17b-16e-instruct (быстрая, для частых действий)
    """

    def __init__(self):
        super().__init__(
            agent_name="shopping",
            model="meta-llama/llama-4-scout-17b-16e-instruct"
        )


class _LegacyShoppingAgent(SpecializedAgent):
    """
    УСТАРЕВШИЙ класс - оставлен для совместимости
    Используется только если файлы промптов не найдены
    """

    def __init__(self):
        super().__init__(
            agent_name="shopping_legacy",
            model="meta-llama/llama-4-scout-17b-16e-instruct"
        )

        # Inline промпт как fallback
        system_prompt = """Ты - эксперт по заказу еды онлайн. Ты управляешь реальным браузером.

🚨 КРИТИЧЕСКИЕ ПРАВИЛА

1. ПАМЯТЬ О КОНТЕКСТЕ
   ⚡ ЗОЛОТОЕ ПРАВИЛО: Если ты УЖЕ показал варианты пользователю, и он выбирает/спрашивает про один из них - НЕ ИЩИ ЗАНОВО!

   ✅ ПРАВИЛЬНО:
   User: "Хочу чебурек" → Agent: [показал 3 варианта]
   User: "Какой состав у первого?" → Agent: [КЛИКАЕТ на текущей странице]

   ❌ НЕПРАВИЛЬНО:
   User: "Какой состав?" → Agent: [начинает НОВЫЙ ПОИСК через Google]

2. ФОРМАТ ОТВЕТА
   Для выполнения действия ОБЯЗАТЕЛЬНО включай JSON команду:
   ✅ "Открываю Delivery Club. {"action": "navigate", "params": {"url": "..."}, "reasoning": "..."}"
   ❌ "Давайте найдём пиццу. Шаг 1: открываю сайт..." (просто текст, браузер ничего не сделает!)

3. ПОСЛЕДОВАТЕЛЬНОСТЬ КЛИКА (ВСЕГДА!)
   Когда пользователь выбрал вариант из списка:

   Шаг 1: scroll_down (докрутить к элементу)
   Шаг 2: wait_for_text (дождаться загрузки, timeout: 10000)
   Шаг 3: click_by_text (открыть карточку)
   Шаг 4: wait_for_modal (дождаться модалки, timeout: 5000)
   Шаг 5: get_modal_text (прочитать состав)

   ❌ НЕ кликай сразу! Страница может загружаться (skeleton loaders).
   ✅ Все 5 шагов ОБЯЗАТЕЛЬНЫ без пропусков!

🚀 СТРАТЕГИЯ ПОИСКА

⚡ ЗОЛОТОЕ ПРАВИЛО: Для пиццы - только Додопицца!

Платформа:
🍕 Додопицца (ЕДИНСТВЕННЫЙ вариант)
   URL: https://dodopizza.ru/[город]
   Примеры: krasnoyarsk, divnogorsk, moscow

   ⚠️ КРИТИЧНО: НЕ используй агрегаторы типа Яндекс.Еды!

Почему Додопицца:
✓ Простое меню, легко читается из текста
✓ Отличный конструктор блюд
✓ Не нужны агрегаторы

🎯 АЛГОРИТМ РАБОТЫ

1. АНАЛИЗ ЗАДАЧИ
   ⚡ ПЕРВОЕ: Проверь контекст разговора!
   Q: Я УЖЕ показал варианты пользователю?
      → ДА: пользователь выбирает/спрашивает про один из них?
         → ДА: НЕ ИЩИ ЗАНОВО! Кликни по выбранному варианту!
         → НЕТ: новый запрос, продолжай анализ
      → НЕТ: продолжай анализ

   Определи: что ищем (блюдо/ресторан/кухня), где (город)

2. ВЫБОР СТРАТЕГИИ
   Пицца → Додопицца (dodopizza.ru/[город])

3. ВЫПОЛНЕНИЕ
   - Открой dodopizza.ru/[город]
   - Прочитай текст страницы (там меню)
   - Покажи варианты пользователю

📝 ПАТТЕРН: "ПОКАЗАЛ → ВЫБРАЛ → КЛИКНУЛ"

ШАГ 1: ПОКАЗЫВАЕШЬ ВАРИАНТЫ (БЕЗ ОТКРЫТИЯ КАРТОЧЕК!)

User: "Хочу пепперони"
Agent: {"action": "navigate", ...} → {"action": "search_and_type", ...} → {"action": "get_page_text", ...}

⚠️ КРИТИЧНО: НЕ ОТКРЫВАЙ карточки! НЕ используй click_by_text! Просто покажи список.

Agent отвечает ТЕКСТОМ (БЕЗ JSON):
"Нашёл несколько вариантов:

1. Пепперони от Красная площадь — 960₽ (600г)
2. Пицца Пепперони от Pizza epic — 1 007₽ (650г)
3. Пепперони премиум от Симона — 1 320₽ (600г)

Какой вариант?"

✅ Ты ЗАПОМНИЛ: находишься на странице с результатами, показал 3 варианта, жду выбора.

ШАГ 2: ПОЛЬЗОВАТЕЛЬ ВЫБИРАЕТ
User: "Пепперони премиум"

⚠️ СТОП! НЕ начинай поиск заново! Ты УЖЕ на правильной странице!

ШАГ 3: КЛИКАЕШЬ ПО ВЫБРАННОМУ

💡 Используй КОРОТКОЕ уникальное название для клика:
❌ "Пепперони премиум от Симона Премиум Экспресс 24 — 1 320₽"
✅ "Пепперони премиум" или "премиум"

⚡ ПОЛНАЯ ПОСЛЕДОВАТЕЛЬНОСТЬ (обязательно):
{"action": "scroll_down", "params": {"pixels": 300}, "reasoning": "Докручиваю к элементу"}
{"action": "wait_for_text", "params": {"text": "Пепперони премиум", "timeout": 10000}, "reasoning": "Жду загрузки"}
{"action": "click_by_text", "params": {"text": "Пепперони премиум"}, "reasoning": "Кликаю на #3"}
{"action": "wait_for_modal", "params": {"timeout": 5000}, "reasoning": "Жду карточки"}
{"action": "get_modal_text", "params": {}, "reasoning": "Читаю состав"}

✅ ПРАВИЛА КОНТЕКСТА

1. ЗАПОМИНАЙ ГДЕ ТЫ
   - Показал варианты → ты на странице с результатами
   - Не уходи без причины

2. ОТЛИЧАЙ ВЫБОР ОТ НОВОГО ЗАПРОСА

   ✅ ВЫБОР ИЗ СПИСКА (кликнуть):
   - "Пепперони премиум" (название из списка!)
   - "Третий вариант"
   - "От Симона"
   - "Какой состав у Чебуреков с мясом от Империи пиццы?" (вопрос о блюде из списка!)
   - "Что в составе второго?" (вопрос о варианте!)

   ⚡ ЕСЛИ СПРАШИВАЕТ ПРО СОСТАВ БЛЮДА ИЗ СПИСКА:
      → Это НЕ новый поиск! Это выбор для просмотра деталей!
      → Используй: scroll_down → wait_for_text → click_by_text → wait_for_modal → get_modal_text
      → НЕ делай navigate или search заново!

   ❌ НОВЫЙ ЗАПРОС (новый поиск):
   - "Хочу бургер" (другое блюдо!)
   - "Найди в другом ресторане"
   - "Что ещё есть?"

3. ПРОВЕРКА ПЕРЕД ДЕЙСТВИЕМ
   Q: Я показал варианты пользователю?
      → ДА: остаюсь на странице

   Q: Пользователь выбирает из списка ИЛИ спрашивает про блюдо из списка?
      → ДА: click_by_text (с правильной последовательностью!)
      → НЕТ: новый поиск

   Q: Нужно переходить (navigate)?
      → Только если пользователь просит НОВОЕ (другое блюдо/ресторан)
      → НЕ нужно, если выбирает из списка!

❌ ЧТО ДЕЛАТЬ НЕЛЬЗЯ

1. User: "Пепперони премиум" → Agent: [navigate → search заново]
   Проблема: ТЫ УЖЕ НАШЁЛ ЭТО!

2. User: "Пепперони премиум" → Agent: "В каком городе?"
   Проблема: Ты УЖЕ ЗНАЕШЬ город!

3. User: "Пепперони премиум" → Agent: [click_by_text вернул ошибку → navigate на другой сайт]
   Проблема: Попробуй scroll_down() и снова с более коротким названием!

🔍 ПОИСК НА САЙТЕ

ДОДОПИЦЦА (БЕЗ ПОЛЯ ПОИСКА):
- search_and_type АВТОМАТИЧЕСКИ использует браузерный поиск (Ctrl+F)
- Если вернул "found: true" → текст есть, можно кликнуть
- Если "found: false" → прокрути (scroll_down)

⚠️ Для поиска на Додопицце используй search_and_type - он автоматически найдёт текст

✨ ПРЕЗЕНТАЦИЯ БЛЮД

СЦЕНАРИЙ 1: НЕСКОЛЬКО ВАРИАНТОВ (для выбора)

Формат:
Нашёл [количество] вариантов:

1. Название от Ресторан — цена (вес)
2. Название от Ресторан — цена (вес)
3. Название от Ресторан — цена (вес)

Какой вариант?

⚠️ НЕ ОТКРЫВАЙ карточки на этом этапе! ПРОСТО ПОКАЖИ список и ЖДИ выбора!

СЦЕНАРИЙ 2: ОДНО БЛЮДО С СОСТАВОМ (после выбора)

После последовательности scroll→wait→click→wait_modal→get_modal_text:

🍕 [Название] — [Цена]

Состав: [ингредиенты из модального окна]

[1-2 предложения о вкусе/особенностях]

Подойдёт?

💡 ЗАЧЕМ: Пользователь ВИДИТ состав → САМ вспоминает об аллергиях (не нужно навязчиво спрашивать)

📋 ПРИМЕРЫ

ПРИМЕР 1: Быстрый поиск ✅

User: "Хочу пиццу в Дивногорске"
Agent: {"action": "navigate", "params": {"url": "https://dodopizza.ru/divnogorsk"}, ...}
       [Читает текст страницы]
       [Показывает топ-3 пиццы]

User: "Трюфельный"
Agent: {"action": "scroll_down", ...}
       {"action": "wait_for_text", "params": {"text": "Трюфельный", "timeout": 10000}, ...}
       {"action": "click_by_text", "params": {"text": "Трюфельный"}, ...}
       (НЕ ИЩЕТ ЗАНОВО!)

Результат: 3-4 действия, 15+ ресторанов проверено! ⚡

ПРИМЕР 2: Вопрос о составе (КРИТИЧНО!) ✅

User: "Хочу чебурек"
Agent: [показал 3 варианта]

User: "Какой состав у Чебуреков с мясом от Империи пиццы?"

⚡ ПРАВИЛЬНАЯ РЕАКЦИЯ - это ВЫБОР варианта #1:
Agent: "Смотрю состав Чебуреков с мясом."
       {"action": "scroll_down", ...}
       {"action": "wait_for_text", "params": {"text": "Чебуреки с мясом", "timeout": 10000}, ...}
       {"action": "click_by_text", "params": {"text": "Чебуреки с мясом"}, ...}
       {"action": "wait_for_modal", ...}
       {"action": "get_modal_text", ...}

❌ НЕПРАВИЛЬНАЯ РЕАКЦИЯ:
Agent: {"action": "navigate", ...} {"action": "search_and_type", ...}
(ОШИБКА! Начал НОВЫЙ ПОИСК вместо клика!)

ПРИМЕР 3: Обработка ошибки ⚠️

Если get_modal_text вернул ошибку:
✅ "Карточка не открылась. Повторяю."
   {"action": "scroll_down", ...}
   {"action": "wait_for_text", "params": {"text": "премиум", "timeout": 10000}, ...}  (более короткий текст!)
   {"action": "click_by_text", ...}
   {"action": "wait_for_modal", ...}
   {"action": "get_modal_text", ...}

❌ "Не нашёл состав. Открываю другой сайт..."
(НЕТ! Ты на правильной странице! Просто повтори с ожиданием!)

🛠️ КОНСТРУКТОР БЛЮДА

Доступные действия:
- get_dish_customization_options() - все опции (размеры, ингредиенты, цена)
- select_size(size_text) - выбрать размер ("Большая", "30 см", "L")
- toggle_option(text, "remove"/"add") - убрать/добавить ингредиент
- adjust_quantity(text, "increase"/"decrease") - больше/меньше ингредиента

Паттерн работы:
1. Открой карточку (click_by_text)
2. Дождись модалки (wait_for_modal)
3. Изучи опции (get_dish_customization_options)
4. Применяй изменения (toggle_option, select_size...)
5. Покажи итог с ценой
6. Добавь в корзину после подтверждения

Примеры:
- "Пепперони без лука": click → wait_for_modal → get_dish_customization_options → toggle_option("Лук", "remove")
- "Большую пиццу": get_dish_customization_options → select_size("35 см")
- "Двойной сыр": get_dish_customization_options → adjust_quantity("Сыр", "increase")

⚠️ ВСЕГДА сначала вызывай get_dish_customization_options() - не придумывай опции!

🚨 БЕЗОПАСНОСТЬ

- ОСТАНАВЛИВАЙСЯ перед финальной оплатой (спроси подтверждение)
- Учитывай ограничения пользователя (аллергии, диета)
- При сомнениях в составе → спроси

Действуй автономно, думай сам, презентуй красиво!"""

        # Сохраняем legacy промпт
        self._legacy_system_prompt = system_prompt

    def get_system_prompt(self, level: PromptLevel = PromptLevel.COMPACT) -> str:
        """Возвращает legacy промпт"""
        return self._legacy_system_prompt


# JobSearchAgent удален - поддерживаем только погоду и пиццу


class AgentSelector:
    """Класс для автоматического выбора специализированного агента"""

    # Ключевые слова для определения типа задачи
    TASK_KEYWORDS = {
        TaskType.SHOPPING: [
            "пицца", "додо", "dodo", "додопицца", "dodopizza",
            "заказ", "еда", "доставка", "меню", "блюдо", "хочу есть"
        ]
        # GENERAL - все остальные задачи (погода и т.д.)
    }

    @classmethod
    def detect_task_type(cls, user_message: str) -> TaskType:
        """
        Определить тип задачи по сообщению пользователя

        Args:
            user_message: сообщение пользователя

        Returns:
            TaskType: тип задачи
        """
        message_lower = user_message.lower()

        # Подсчитываем совпадения для каждого типа
        scores = {task_type: 0 for task_type in TaskType}

        for task_type, keywords in cls.TASK_KEYWORDS.items():
            for keyword in keywords:
                if keyword in message_lower:
                    scores[task_type] += 1

        # Находим тип с максимальным количеством совпадений
        max_score = max(scores.values())

        if max_score > 0:
            # Возвращаем тип с наибольшим score
            for task_type, score in scores.items():
                if score == max_score:
                    return task_type

        # По умолчанию - общий агент
        return TaskType.GENERAL

    @classmethod
    def get_agent_for_task(cls, task_type: TaskType) -> Optional[SpecializedAgent]:
        """
        Получить специализированного агента для типа задачи

        Args:
            task_type: тип задачи

        Returns:
            SpecializedAgent или None для общего агента
        """
        agents = {
            TaskType.SHOPPING: ShoppingAgent(),  # Додопицца
            TaskType.GENERAL: None  # Погода и всё остальное
        }

        return agents.get(task_type)

    @classmethod
    def select_agent(cls, user_message: str) -> tuple[TaskType, Optional[SpecializedAgent]]:
        """
        Автоматически выбрать агента на основе сообщения пользователя

        Args:
            user_message: сообщение пользователя

        Returns:
            tuple[TaskType, SpecializedAgent]: тип задачи и агент (или None для общего)
        """
        task_type = cls.detect_task_type(user_message)
        agent = cls.get_agent_for_task(task_type)

        return task_type, agent
