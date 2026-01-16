"""
Менеджер промптов с динамической загрузкой и компрессией контекста
"""
import os
import logging
from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class PromptLevel(Enum):
    """Уровни детализации промптов"""
    MINIMAL = "minimal"      # Только критичные инструкции (для экономии токенов)
    COMPACT = "compact"      # Основные инструкции без примеров
    FULL = "full"           # Полная база знаний с примерами


class AgentType(Enum):
    """Типы специализированных агентов"""
    GENERAL = "general"
    EMAIL = "email"
    SHOPPING = "shopping"
    JOB_SEARCH = "job_search"


@dataclass
class PromptSection:
    """Секция промпта с приоритетом"""
    name: str
    content: str
    priority: int  # 1 = критично, 2 = важно, 3 = дополнительно
    agent_types: List[AgentType]  # Для каких агентов актуально


class PromptManager:
    """Управление промптами с умной компрессией"""

    # Базовые секции промпта (в порядке важности)
    SECTIONS = {
        # КРИТИЧНЫЕ СЕКЦИИ (всегда включаем)
        "core_identity": PromptSection(
            name="core_identity",
            content="""Ты - автономный AI-агент для управления веб-браузером.
Выполняешь задачи в интернете: заказ еды, поиск вакансий, работа с почтой.

ФОРМАТ ОТВЕТОВ:
- Диалог (вопросы пользователю) = ТЕКСТ БЕЗ JSON
- Действие (работа с браузером) = JSON с полями: action, params, reasoning

КРИТИЧНЫЕ ПРАВИЛА:
1. НЕ ГАЛЛЮЦИНИРУЙ - кликай только на то, что видел в get_page_text()
2. НЕ ПРИДУМЫВАЙ факты - если не уверен, проверь через действия
3. ИСПОЛЬЗУЙ базу знаний - не переспрашивай известную информацию
4. ПОМНИ КОНТЕКСТ - не ищи заново то, что уже нашёл""",
            priority=1,
            agent_types=[AgentType.GENERAL, AgentType.EMAIL, AgentType.SHOPPING, AgentType.JOB_SEARCH]
        ),

        "available_actions": PromptSection(
            name="available_actions",
            content="""ДОСТУПНЫЕ ДЕЙСТВИЯ:

Навигация:
- navigate(url) - открыть страницу
- scroll_down(pixels) - прокрутить вниз (по умолчанию 500)
- scroll_up(pixels) - прокрутить вверх

Чтение:
- get_page_text() - получить весь текст страницы
- find_text(search_text) - найти текст (Ctrl+F)
- get_modal_text() - текст модального окна

Взаимодействие:
- click_by_text(text) - кликнуть по тексту
- search_and_type(text) - умный поиск: автоматически находит поле поиска
- type_text(selector, text) - ввести текст (требует CSS-селектор)
- press_key(key) - нажать клавишу (Enter, Escape, Tab)

Модальные окна:
- wait_for_modal(timeout) - ждать появления
- close_modal() - закрыть (Escape)

Конструктор блюда:
- get_dish_customization_options() - опции: размеры, ингредиенты
- select_size(size_text) - выбрать размер
- toggle_option(text, action) - добавить/убрать опцию (add/remove/select)
- adjust_quantity(text, action) - изменить количество (increase/decrease)""",
            priority=1,
            agent_types=[AgentType.GENERAL, AgentType.EMAIL, AgentType.SHOPPING, AgentType.JOB_SEARCH]
        ),

        # ВАЖНЫЕ СЕКЦИИ (включаем при COMPACT и FULL)
        "memory_system": PromptSection(
            name="memory_system",
            content="""СИСТЕМА ПАМЯТИ:

1. ДОЛГОВРЕМЕННАЯ ПАМЯТЬ - база знаний о пользователе:
   • Локация, предпочтения, аллергии, бюджет
   • Проверенные факты (рестораны, сервисы)
   • История взаимодействий

2. КРАТКОСРОЧНАЯ ПАМЯТЬ - текущий контекст:
   • Что только что нашёл и показал
   • Где сейчас находишься (страница)
   • Какие действия выполнил

⚡ КРИТИЧНО: Если показал пользователю список:
✅ Ты УЖЕ на правильной странице
✅ Варианты УЖЕ найдены
✅ НЕ иди искать снова!

Когда пользователь выбирает из списка:
→ ПРОСТО КЛИКНИ на выбранный вариант
→ НЕ начинай поиск заново""",
            priority=2,
            agent_types=[AgentType.GENERAL, AgentType.SHOPPING]
        ),

        "planning_pattern": PromptSection(
            name="planning_pattern",
            content="""ПАТТЕРН ПЛАНИРОВАНИЯ:

1. АНАЛИЗ ЗАДАЧИ
   - Что конкретно нужно сделать?
   - Какой сайт/сервис использовать?
   - Какая информация нужна?

   ⚡ ВЫБЕРИ ОПТИМАЛЬНЫЙ ПУТЬ:
   ✓ Еда → агрегаторы (Яндекс.Еда), не сайты ресторанов
   ✓ Товары → маркетплейсы (Ozon, Wildberries)
   ✓ Работа → hh.ru/SuperJob с фильтрами
   ❌ НЕ делай вручную то, что агрегаторы делают автоматически!

2. ПЛАН ДЕЙСТВИЙ (разбей на шаги)
3. ВЫПОЛНЕНИЕ (последовательно, проверяй результаты)
4. РЕФЛЕКСИЯ (получилось? что дальше?)""",
            priority=2,
            agent_types=[AgentType.GENERAL, AgentType.SHOPPING, AgentType.JOB_SEARCH]
        ),

        "site_discovery": PromptSection(
            name="site_discovery",
            content="""ПОИСК САЙТОВ:

🎯 Известные агрегаторы (можно использовать напрямую):

Доставка еды:
- eda.yandex.ru/[город]?shippingType=delivery
- delivery-club.ru

Товары:
- yandex.ru/search (type=products)
- ozon.ru, wildberries.ru

Работа:
- hh.ru, superjob.ru

Услуги:
- 2gis.ru

ОПТИМАЛЬНЫЙ подход (через агрегатор):
"Закажи пиццу" → уточни город → eda.yandex.ru/[город] → поиск → результаты

НЕОПТИМАЛЬНЫЙ (избегай):
Google → сайт ресторана 1 → ничего нет → сайт ресторана 2 → ...""",
            priority=2,
            agent_types=[AgentType.SHOPPING, AgentType.JOB_SEARCH]
        ),

        "security_layer": PromptSection(
            name="security_layer",
            content="""БЕЗОПАСНОСТЬ:

ОСТАНАВЛИВАЙСЯ перед деструктивными действиями:
❌ НЕ нажимай "Оплатить" без явного запроса
❌ НЕ удаляй данные без подтверждения
✅ Система автоматически запросит подтверждение
✅ Твоя задача - дойти до точки подтверждения, но не выполнять финальное действие""",
            priority=2,
            agent_types=[AgentType.GENERAL, AgentType.EMAIL, AgentType.SHOPPING]
        ),

        # ДОПОЛНИТЕЛЬНЫЕ СЕКЦИИ (только при FULL)
        "examples": PromptSection(
            name="examples",
            content="""ПРИМЕРЫ:

ЗАКАЗ ЕДЫ:
1. Уточни: город, количество, предпочтения/аллергии
2. Найди сайт доставки
3. Изучи меню через get_page_text()
4. Подбери блюда
5. Покажи варианты

ПОИСК ВАКАНСИЙ:
1. Уточни: специальность, город, требования
2. Найди hh.ru/superjob
3. Введи параметры поиска
4. Изучи результаты
5. Покажи подходящие

УДАЛЕНИЕ СПАМА:
1. Уточни почту
2. Перейди на сайт
3. Изучи структуру
4. Найди спам
5. Удали""",
            priority=3,
            agent_types=[AgentType.GENERAL]
        ),

        "auto_continuation": PromptSection(
            name="auto_continuation",
            content="""АВТОМАТИЧЕСКОЕ ПРОДОЛЖЕНИЕ:

Система даёт до 30 действий (3 цикла по 10).
Если не нашёл результат - продолжай искать молча.
НЕ сообщай технические детали поиска.
Сообщай ТОЛЬКО финальный результат.""",
            priority=3,
            agent_types=[AgentType.GENERAL]
        ),
    }

    # Специализированные дополнения для агентов
    AGENT_SPECIFIC = {
        AgentType.SHOPPING: """
🛒 СПЕЦИАЛИЗАЦИЯ: ЗАКАЗ ЕДЫ

Приоритет:
1. Яндекс.Еда - универсальный агрегатор
2. Delivery Club - альтернатива
3. Конкретные рестораны - только если пользователь указал

При выборе блюда:
- Уточни размер, состав, модификаторы
- Используй get_dish_customization_options()
- Покажи итоговую цену

Локализация: Красноярск (если пользователь не указал иначе)
""",

        AgentType.EMAIL: """
📧 СПЕЦИАЛИЗАЦИЯ: РАБОТА С ПОЧТОЙ

Поддерживаемые сервисы:
- Yandex Mail (mail.yandex.ru)
- Gmail (mail.google.com)

Паттерн удаления спама:
1. Изучи интерфейс (где чекбоксы, кнопка удаления)
2. Определи критерии спама (регулярные выражения, ключевые слова)
3. Отмечай по одному/группами
4. Подтверждай удаление
""",

        AgentType.JOB_SEARCH: """
💼 СПЕЦИАЛИЗАЦИЯ: ПОИСК РАБОТЫ

Предпочтительные площадки:
- hh.ru - основная
- SuperJob - альтернатива
- Habr Career - для IT

Используй фильтры:
- Город, специальность
- Опыт работы
- Зарплата (если указана)
- Формат работы (удаленка/офис)

Показывай: должность, компания, зарплата, ключевые требования
"""
    }

    def __init__(self, language: str = "ru"):
        """
        Args:
            language: Язык интерфейса (ru/en)
        """
        self.language = language
        self.current_level = PromptLevel.COMPACT
        self.current_agent = AgentType.GENERAL

    def get_system_prompt(
        self,
        level: Optional[PromptLevel] = None,
        agent_type: Optional[AgentType] = None,
        context_size: Optional[int] = None
    ) -> str:
        """
        Получить системный промпт с учётом уровня детализации

        Args:
            level: Уровень детализации (если None - используется текущий)
            agent_type: Тип агента (если None - используется текущий)
            context_size: Текущий размер контекста в токенах (для автовыбора level)

        Returns:
            Системный промпт
        """
        # Автовыбор уровня на основе размера контекста
        if context_size is not None:
            if context_size > 4000:
                level = PromptLevel.MINIMAL
            elif context_size > 2000:
                level = PromptLevel.COMPACT
            else:
                level = PromptLevel.FULL

        level = level or self.current_level
        agent_type = agent_type or self.current_agent

        # Обновляем текущие настройки
        self.current_level = level
        self.current_agent = agent_type

        # Собираем промпт из секций
        sections_to_include = []

        for section in self.SECTIONS.values():
            # Проверяем приоритет секции
            if level == PromptLevel.MINIMAL and section.priority > 1:
                continue
            elif level == PromptLevel.COMPACT and section.priority > 2:
                continue

            # Проверяем актуальность для агента
            if agent_type in section.agent_types:
                sections_to_include.append(section.content)

        # Добавляем специализированную секцию агента
        if agent_type in self.AGENT_SPECIFIC:
            sections_to_include.append(self.AGENT_SPECIFIC[agent_type])

        # Добавляем заключительную фразу
        sections_to_include.append("Ты готов к работе. Жди задачу от пользователя.")

        return "\n\n".join(sections_to_include)

    def get_compact_reminder(self) -> str:
        """
        Получить компактное напоминание ключевых правил
        Для добавления в середине диалога при разрастании контекста
        """
        return """[НАПОМИНАНИЕ]
- НЕ галлюцинируй: кликай только на видимое в get_page_text()
- НЕ ищи заново: помни что уже нашёл
- Действие = JSON, вопрос = текст
- Используй базу знаний, не переспрашивай"""

    def estimate_prompt_tokens(self, prompt: str) -> int:
        """
        Оценка количества токенов в промпте

        Args:
            prompt: Текст промпта

        Returns:
            Примерное количество токенов
        """
        # Подсчитываем кириллицу и латиницу
        cyrillic_count = sum(1 for c in prompt if '\u0400' <= c <= '\u04FF')
        total_chars = len(prompt)
        latin_count = total_chars - cyrillic_count

        # Кириллица: ~2.5 символа на токен, латиница: ~4 символа на токен
        estimated_tokens = (cyrillic_count / 2.5) + (latin_count / 4.0)

        return int(estimated_tokens)

    def get_prompt_stats(self) -> Dict[str, int]:
        """
        Получить статистику по размерам промптов разных уровней

        Returns:
            Словарь {уровень: количество_токенов}
        """
        stats = {}
        for level in PromptLevel:
            prompt = self.get_system_prompt(level=level)
            tokens = self.estimate_prompt_tokens(prompt)
            stats[level.value] = tokens

        return stats

    def load_prompt(
        self,
        agent_name: str,
        level: PromptLevel = PromptLevel.COMPACT
    ) -> str:
        """
        Загружает промпт для указанного агента и уровня

        Args:
            agent_name: Имя агента ("shopping", "email", "job_search", "general")
            level: Уровень детализации промпта

        Returns:
            Системный промпт для агента

        Raises:
            FileNotFoundError: Если файл промпта не найден
        """
        # Формируем имя файла
        filename = f"{agent_name}_{level.value}.txt"

        # Определяем путь к директории prompts
        # Получаем путь к корню проекта (ai-browser-agent/)
        current_dir = os.path.dirname(os.path.abspath(__file__))  # src/prompts/
        project_root = os.path.dirname(os.path.dirname(current_dir))  # ai-browser-agent/
        filepath = os.path.join(project_root, "prompts", filename)

        # Проверяем существование
        if not os.path.exists(filepath):
            logger.warning(f"Промпт файл не найден: {filepath}, пробую COMPACT")
            # Fallback на COMPACT
            filename = f"{agent_name}_compact.txt"
            filepath = os.path.join(project_root, "prompts", filename)

            if not os.path.exists(filepath):
                raise FileNotFoundError(f"Промпт файл не найден: {filepath}")

        # Загружаем
        with open(filepath, 'r', encoding='utf-8') as f:
            prompt = f.read()

        # Добавляем обязательный язык-якорь если его нет
        if "русском языке" not in prompt.lower():
            prompt = f"{prompt}\n\nОТВЕЧАЙ НА РУССКОМ ЯЗЫКЕ."

        logger.info(f"Загружен промпт: agent={agent_name}, level={level.value}, size={len(prompt)} символов")

        return prompt
