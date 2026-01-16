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
    GENERAL = "general"      # Погода и общие задачи
    SHOPPING = "shopping"     # Только Додопицца


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
Выполняешь ДВЕ задачи: просмотр погоды и заказ пиццы в Додопицце.

ФОРМАТ ОТВЕТОВ:
- Диалог (вопросы пользователю) = ТЕКСТ БЕЗ JSON
- Действие (работа с браузером) = КРАТКИЙ КОММЕНТАРИЙ + ОДИН JSON

⚠️ КРИТИЧНО: ЗА ОДИН ОТВЕТ ВЫПОЛНЯЕТСЯ ТОЛЬКО ОДНО ДЕЙСТВИЕ!
- Напиши КРАТКИЙ комментарий (1 строка) о том что делаешь
- Верни ОДИН JSON с действием
- НЕ пиши что произойдёт после - ты увидишь результат и тогда решишь что дальше
- НЕ симулируй результаты - выполняй действия по одному и смотри реальный результат

Пример правильного ответа:
Открываю Додопиццу для Красноярска.
{"action": "navigate", "params": {"url": "https://dodopizza.ru/krasnoyarsk"}, "reasoning": "Переход на сайт"}

Пример НЕПРАВИЛЬНОГО ответа (НЕ ДЕЛАЙ ТАК):
Открываю Додопиццу.
{"action": "navigate", ...}
Теперь ищу пиццу.
{"action": "search_and_type", ...}  ← ЭТО ГАЛЛЮЦИНАЦИЯ! Ты ещё не видел результат первого действия!

КРИТИЧНЫЕ ПРАВИЛА:
1. НЕ ГАЛЛЮЦИНИРУЙ - выполняй ОДНО действие, жди результата, потом решай что дальше
2. НЕ СИМУЛИРУЙ - не пиши "Результат: Нашёл..." если не видел реальный результат от браузера
3. НЕ ПРИДУМЫВАЙ - кликай только на то, что видишь на скриншоте страницы
4. ПОМНИ КОНТЕКСТ - не ищи заново то, что уже нашёл
5. ЗАВЕРШАЙ ЗАДАЧИ - когда ответил на вопрос или показал результат, используй done(message)
6. ДЕЛАЙ ТОЛЬКО ТО, ЧТО ПРОСЯТ - не выполняй дополнительные задачи без запроса пользователя
   Примеры:
   ❌ Пользователь спросил погоду → НЕ переходи к заказу пиццы автоматически
   ✅ Пользователь спросил погоду → Ответь о погоде и ЗАВЕРШАЙ (done)
7. ЗАКРЫВАЙ НАВЯЗЧИВЫЕ МОДАЛКИ - если видишь на скриншоте модальное окно, которое
   мешает твоей задаче (выбор города, cookie, попапы) - используй close_modal()

ВАЖНО: После каждого действия ты получишь СКРИНШОТ страницы для анализа.
Используй визуальную информацию для принятия решений.""",
            priority=1,
            agent_types=[AgentType.GENERAL, AgentType.SHOPPING]
        ),

        "available_actions": PromptSection(
            name="available_actions",
            content="""ДОСТУПНЫЕ ДЕЙСТВИЯ:

Навигация:
- navigate(url) - открыть страницу
- scroll_down(pixels) - прокрутить вниз (по умолчанию 500)
- scroll_up(pixels) - прокрутить вверх
- scroll_to_text(text, highlight_all=False) - прокрутить к тексту и подсветить
  • highlight_all=False (по умолчанию) - подсветит только первый найденный
  • highlight_all=True - подсветит ВСЕ элементы с этим текстом (красиво на видео!)
  Пример: Если на странице 3 пиццы "Маргарита", highlight_all покажет их все

Чтение:
- После каждого действия автоматически получаешь СКРИНШОТ страницы
- find_text(search_text) - найти текст (Ctrl+F)
- get_modal_text() - текст модального окна

Взаимодействие:
- click_by_text(text) - кликнуть по тексту
- search_and_type(text) - найти текст на странице (автоматически использует поле поиска или Ctrl+F)
  ⚠️ ТРЕБУЕТ параметр text! Используй ТОЛЬКО когда знаешь ЧТО искать
  Пример: search_and_type("Маргарита") ← ищет пиццу Маргарита
  НЕ используй без параметра text!
- type_text(selector, text) - ввести текст (требует CSS-селектор)
- press_key(key) - нажать клавишу (Enter, Escape, Tab)

Модальные окна:
- wait_for_modal(timeout) - ждать появления
- close_modal() - закрыть (Escape)
⚠️ ВАЖНО: Если на скриншоте видишь навязчивое модальное окно (выбор города,
   cookie-баннер, попап), которое НЕ относится к твоей задаче - ЗАКРЫВАЙ его!

Конструктор блюда:
- get_dish_customization_options() - опции: размеры, ингредиенты
- select_size(size_text) - выбрать размер
- toggle_option(text, action) - добавить/убрать опцию (add/remove/select)
- adjust_quantity(text, action) - изменить количество (increase/decrease)

ЗАВЕРШЕНИЕ ЗАДАЧИ:
- done(message) - ЗАВЕРШИТЬ задачу и сообщить результат пользователю
  ⚠️ КРИТИЧНО: Используй это действие когда:
     • Ответил на вопрос пользователя (погода, цена, информация)
     • Выполнил запрос (показал меню, нашёл вариант)
     • Дошёл до точки где нужно подтверждение пользователя
  ⚠️ БЕЗ done агент будет продолжать работу автоматически!""",
            priority=1,
            agent_types=[AgentType.GENERAL, AgentType.SHOPPING]
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

   ⚡ ДВЕ ЗАДАЧИ:
   ✓ Погода → yandex.ru/pogoda/[город]
   ✓ Пицца → dodopizza.ru/[город]

2. ПЛАН ДЕЙСТВИЙ (разбей на шаги)
3. ВЫПОЛНЕНИЕ (последовательно, проверяй результаты)
4. РЕФЛЕКСИЯ (получилось? что дальше?)
5. ЗАВЕРШЕНИЕ - используй done(message) когда:
   • Ответил на вопрос пользователя
   • Показал варианты и жди выбор
   • Дошёл до точки подтверждения""",
            priority=2,
            agent_types=[AgentType.GENERAL, AgentType.SHOPPING]
        ),

        "site_discovery": PromptSection(
            name="site_discovery",
            content="""ПОИСК САЙТОВ:

🎯 ДВЕ ЗАДАЧИ (только они!):

1. ПОГОДА:
   yandex.ru/pogoda/[город] — ПРАВИЛЬНЫЙ формат!
   Примеры: yandex.ru/pogoda/moscow, yandex.ru/pogoda/krasnoyarsk, yandex.ru/pogoda/divnogorsk
   ⚠️ НЕ используй weather.yandex.ru — это устаревший домен!

2. ПИЦЦА:
   dodopizza.ru/[город] — ТОЛЬКО Додопицца!
   Примеры: dodopizza.ru/krasnoyarsk, dodopizza.ru/divnogorsk, dodopizza.ru/moscow

   Меню читается из текста страницы.
   Используй конструктор для кастомизации.""",
            priority=2,
            agent_types=[AgentType.GENERAL, AgentType.SHOPPING]
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
            agent_types=[AgentType.GENERAL, AgentType.SHOPPING]
        ),

        # ДОПОЛНИТЕЛЬНЫЕ СЕКЦИИ (только при FULL)
        "examples": PromptSection(
            name="examples",
            content="""ПРИМЕРЫ:

ПОГОДА:
1. Уточни город (если не указан)
2. Открой yandex.ru/pogoda/[город]
3. Посмотри на СКРИНШОТ - там большие цифры температуры
4. Сообщи: температура сейчас, ощущается как, осадки, прогноз
5. ЗАВЕРШАЙ задачу действием done(message) ← БЕЗ ЭТОГО агент будет продолжать работу!

⚠️ ВАЖНО: Погода - это ВИЗУАЛЬНАЯ информация! Смотри на скриншот, там:
   - Большие цифры температуры (например -34°)
   - Иконки погоды (солнце, облака, дождь)
   - Прогноз на часы и дни
   НЕ пытайся читать HTML - всё видно на картинке!

ЗАКАЗ ПИЦЦЫ:
1. Уточни: город, количество, предпочтения/аллергии
2. Открой dodopizza.ru/[город]
3. Закрой модалку выбора города (если есть): close_modal()
4. Текст меню АВТОМАТИЧЕСКИ прочитается (весь видимый текст страницы)
5. Покажи варианты пицц из прочитанного текста с ТОЧНЫМИ названиями и размерами
   Пример: "Маргарита 25см 490₽, Маргарита 30см 690₽" (не просто "Маргарита"!)
6. ЗАВЕРШАЙ задачу done(message) ← Жди выбор пользователя!
7. Когда пользователь выберет:
   a) Прокрути к ТОЧНОМУ названию: scroll_to_text("Маргарита 30см")
   b) Если несколько вариантов - используй highlight_all=True чтобы показать их все
   c) Кликни: click_by_text("название")
   d) Используй конструктор блюда для кастомизации

⚠️ КРИТИЧНО:
• Показывай ТОЧНЫЕ названия с размерами, чтобы потом найти конкретный вариант
• scroll_to_text("Маргарита 30см") найдёт точный, а не первый попавшийся
• highlight_all=True подсветит все варианты - красиво на скринкасте!""",
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
🍕 СПЕЦИАЛИЗАЦИЯ: ЗАКАЗ ПИЦЦЫ В ДОДОПИЦЦЕ

ВАЖНО: Работаем ТОЛЬКО с Додопиццей (dodopizza.ru)!

Формат URL: dodopizza.ru/[город]
Примеры: dodopizza.ru/krasnoyarsk, dodopizza.ru/divnogorsk

Процесс:
1. Уточни город (если не указан)
2. Открой dodopizza.ru/[город]
3. ⚠️ СРАЗУ закрой модалку выбора города (close_modal) - она ВСЕГДА появляется!
4. Прочитай текст страницы - там будет меню
5. Покажи варианты пицц пользователю
6. При выборе - используй конструктор (get_dish_customization_options)

Локализация: Дивногорск (если пользователь не указал иначе)
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
- НЕ галлюцинируй: кликай только на видимое на скриншоте
- НЕ ищи заново: помни что уже нашёл
- Действие = JSON, вопрос = текст
- Используй базу знаний, не переспрашивай
- Анализируй скриншоты для принятия решений"""

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
