# 📊 Отчет Сессии 2: Система управления промптами с уровнями детализации

**Дата:** 2026-01-16
**Статус:** ✅ Завершено успешно
**Коммит:** `3dd72ac`

---

## 🎯 Цель сессии

Создать систему управления промптами с 3 уровнями детализации для специализированных агентов (ShoppingAgent, EmailAgent, JobSearchAgent) для экономии токенов при сохранении качества работы.

---

## ✅ Выполненные задачи

### 1. Модификация PromptManager

**Файл:** `src/prompts/prompt_manager.py`

**Добавлено:**
- Метод `load_prompt(agent_name: str, level: PromptLevel)` для загрузки промптов из файлов
- Логирование загрузки промптов
- Автоматическое добавление язык-якоря "ОТВЕЧАЙ НА РУССКОМ ЯЗЫКЕ"
- Fallback на COMPACT если файл не найден

```python
def load_prompt(
    self,
    agent_name: str,
    level: PromptLevel = PromptLevel.COMPACT
) -> str:
    """Загружает промпт для указанного агента и уровня"""
    # Формируем имя файла
    filename = f"{agent_name}_{level.value}.txt"
    filepath = os.path.join(project_root, "prompts", filename)

    # Проверяем существование
    if not os.path.exists(filepath):
        logger.warning(f"Промпт файл не найден: {filepath}, пробую COMPACT")
        # Fallback на COMPACT
        filename = f"{agent_name}_compact.txt"
        filepath = os.path.join(project_root, "prompts", filename)

    # Загружаем промпт
    with open(filepath, 'r', encoding='utf-8') as f:
        prompt = f.read()

    # Добавляем язык-якорь
    if "русском языке" not in prompt.lower():
        prompt = f"{prompt}\n\nОТВЕЧАЙ НА РУССКОМ ЯЗЫКЕ."

    return prompt
```

---

### 2. Обновление SpecializedAgent

**Файл:** `src/agent/specialized_agents.py`

**Изменения:**
- Переработан базовый класс `SpecializedAgent` для поддержки уровней
- Добавлено кеширование промптов для оптимизации
- Обновлены `EmailAgent`, `ShoppingAgent`, `JobSearchAgent` для использования системы уровней

**До:**
```python
class SpecializedAgent:
    def __init__(self, model: str, system_prompt: str):
        self.model = model
        self.system_prompt = system_prompt
```

**После:**
```python
class SpecializedAgent:
    def __init__(self, agent_name: str, model: str):
        self.agent_name = agent_name
        self.model = model
        self.prompt_manager = PromptManager()
        self._cached_prompt: Optional[str] = None
        self._cached_level: Optional[PromptLevel] = None

    def get_system_prompt(self, level: PromptLevel = PromptLevel.COMPACT) -> str:
        # Кеширование
        if self._cached_prompt and self._cached_level == level:
            return self._cached_prompt

        # Загрузка
        prompt = self.prompt_manager.load_prompt(self.agent_name, level)

        # Сохранение в кеш
        self._cached_prompt = prompt
        self._cached_level = level

        return prompt
```

---

### 3. Создание файлов промптов

**Директория:** `prompts/`

**Созданные файлы (9 штук):**

#### ShoppingAgent
- `shopping_minimal.txt` - 732 символов, ~230 токенов
- `shopping_compact.txt` - 1491 символов, ~509 токенов
- `shopping_full.txt` - 9520 символов, ~3103 токенов

#### EmailAgent
- `email_minimal.txt` - 546 символов, ~191 токенов
- `email_compact.txt` - 1096 символов, ~379 токенов
- `email_full.txt` - 2788 символов, ~912 токенов

#### JobSearchAgent
- `job_search_minimal.txt` - 433 символов, ~142 токенов
- `job_search_compact.txt` - 1067 символов, ~364 токенов
- `job_search_full.txt` - 3362 символов, ~1092 токенов

---

## 📊 Результаты тестирования

### Сравнение размеров промптов

| Агент       | MINIMAL  | COMPACT  | FULL     |
|-------------|----------|----------|----------|
| Shopping    | ~230 т   | ~509 т   | ~3103 т  |
| Email       | ~191 т   | ~379 т   | ~912 т   |
| JobSearch   | ~142 т   | ~364 т   | ~1092 т  |

### Экономия токенов (MINIMAL vs FULL)

| Агент       | Экономия |
|-------------|----------|
| Shopping    | **92.6%** (2873 токенов) |
| Email       | **79.1%** (721 токенов)  |
| JobSearch   | **87.0%** (950 токенов)  |

### Проверка критериев успеха

#### ✅ ShoppingAgent
- MINIMAL ≤ 300 токенов: **✅ 230 токенов**
- COMPACT ≤ 600 токенов: **✅ 509 токенов**

#### ✅ EmailAgent
- MINIMAL ≤ 250 токенов: **✅ 191 токенов**
- COMPACT ≤ 500 токенов: **✅ 379 токенов**

#### ✅ JobSearchAgent
- MINIMAL ≤ 250 токенов: **✅ 142 токенов**
- COMPACT ≤ 500 токенов: **✅ 364 токенов**

---

## 🏗️ Архитектура системы

```
ai-browser-agent/
├── prompts/
│   ├── shopping_minimal.txt    (~230 токенов)
│   ├── shopping_compact.txt    (~509 токенов)
│   ├── shopping_full.txt       (~3103 токенов)
│   ├── email_minimal.txt       (~191 токенов)
│   ├── email_compact.txt       (~379 токенов)
│   ├── email_full.txt          (~912 токенов)
│   ├── job_search_minimal.txt  (~142 токенов)
│   ├── job_search_compact.txt  (~364 токенов)
│   └── job_search_full.txt     (~1092 токенов)
│
├── src/
│   ├── prompts/
│   │   └── prompt_manager.py   (PromptManager.load_prompt())
│   │
│   └── agent/
│       └── specialized_agents.py
│           ├── SpecializedAgent (базовый класс)
│           ├── ShoppingAgent
│           ├── EmailAgent
│           └── JobSearchAgent
```

---

## 🔧 Как использовать

### Базовое использование

```python
from src.agent.specialized_agents import ShoppingAgent
from src.prompts.prompt_manager import PromptLevel

# Создание агента
agent = ShoppingAgent()

# Загрузка промпта нужного уровня
minimal_prompt = agent.get_system_prompt(PromptLevel.MINIMAL)   # ~230 токенов
compact_prompt = agent.get_system_prompt(PromptLevel.COMPACT)   # ~509 токенов
full_prompt = agent.get_system_prompt(PromptLevel.FULL)         # ~3103 токенов
```

### Динамический выбор уровня

```python
def get_prompt_for_context(agent, context_size):
    """Выбор уровня промпта в зависимости от размера контекста"""
    if context_size > 4000:
        return agent.get_system_prompt(PromptLevel.MINIMAL)
    elif context_size > 2000:
        return agent.get_system_prompt(PromptLevel.COMPACT)
    else:
        return agent.get_system_prompt(PromptLevel.FULL)
```

### Прямая загрузка через PromptManager

```python
from src.prompts.prompt_manager import PromptManager, PromptLevel

pm = PromptManager()

# Загрузка промпта
prompt = pm.load_prompt("shopping", PromptLevel.MINIMAL)

# Оценка размера
tokens = pm.estimate_prompt_tokens(prompt)
print(f"Размер: {tokens} токенов")
```

---

## 🎨 Содержание промптов по уровням

### MINIMAL (~150-250 токенов)
**Цель:** Минимальный набор инструкций для базовой функциональности

**Содержит:**
- Основная роль агента
- Список платформ (приоритет)
- Критические правила (3-4 пункта)
- Базовые доступные действия
- Формат ответа
- Язык-якорь

**Пример (ShoppingAgent):**
```
Ты - агент для заказа еды на русскоязычных платформах.

ПЛАТФОРМЫ:
- Яндекс.Еда (приоритет)
- Delivery Club
- Dodopizza

ПРАВИЛА:
1. Действия передавай ТОЛЬКО через JSON команды
2. Показывай 3-5 вариантов блюд с ценами
3. Спрашивай подтверждение перед заказом
4. Не выдумывай информацию - проверяй на сайте

ДОСТУПНЫЕ ДЕЙСТВИЯ:
- navigate, search_and_type, click_by_text, get_page_text

ФОРМАТ ОТВЕТА:
1. Текст для пользователя (рассуждение)
2. JSON команда (если нужно действие)

ОТВЕЧАЙ НА РУССКОМ ЯЗЫКЕ.
```

### COMPACT (~350-600 токенов)
**Цель:** Основные инструкции с алгоритмами работы без примеров

**Содержит:**
- Расширенное описание роли
- Детальный список платформ с URL
- Алгоритм работы (пошаговый)
- Критерии принятия решений
- Полный список действий с параметрами
- Формат JSON команды
- Критические правила (детально)
- Язык-якорь

**Пример (EmailAgent):**
```
Ты - специализированный агент для управления электронной почтой.

ПОДДЕРЖИВАЕМЫЕ СЕРВИСЫ:
- Яндекс.Почта (https://mail.yandex.ru)
- Gmail (https://mail.google.com)
- Mail.ru (https://mail.ru)

АЛГОРИТМ УДАЛЕНИЯ СПАМА:
1. Открыть почтовый сервис
2. Найти папку "Спам" или использовать поиск
3. Получить список писем
4. ОБЯЗАТЕЛЬНО показать пользователю ЧТО будет удалено
5. Дождаться подтверждения
6. Удалить только подтвержденные письма

КРИТЕРИИ СПАМА:
✅ Удалять: ...
❌ НЕ УДАЛЯТЬ: ...

ФОРМАТ ВЫВОДА: ...
ДОСТУПНЫЕ ДЕЙСТВИЯ: ...

ОТВЕЧАЙ НА РУССКОМ ЯЗЫКЕ.
```

### FULL (~900-3100 токенов)
**Цель:** Полная база знаний с примерами и edge cases

**Содержит:**
- Все из COMPACT
- Детальные примеры использования (✅ правильно / ❌ неправильно)
- Обработка ошибок
- Edge cases и специальные сценарии
- Паттерны презентации результатов
- Мотивация правил ("💡 ЗАЧЕМ ЭТО НУЖНО")
- Специфика платформ
- Безопасность
- Язык-якорь

---

## 🚀 Преимущества системы

### 1. Экономия токенов
- **MINIMAL:** 80-93% экономии vs FULL
- **COMPACT:** 60-84% экономии vs FULL
- Позволяет вместить больше контекста в бюджет токенов

### 2. Гибкость
- Динамический выбор уровня в зависимости от размера контекста
- Fallback на COMPACT если файл не найден
- Кеширование для оптимизации

### 3. Поддерживаемость
- Промпты в отдельных файлах - легко редактировать
- Централизованное управление через PromptManager
- Версионирование промптов через git

### 4. Качество
- Язык-якорь автоматически добавляется
- Логирование загрузки и размеров
- Тестирование всех уровней

---

## 📝 Следующие шаги (рекомендации)

### 1. Интеграция с KnowledgeBase
Связать систему уровней промптов с KnowledgeBase для автоматического выбора:

```python
class AIAgent:
    def get_prompt(self, task_type):
        # Определяем размер контекста
        context_size = self.knowledge_base.estimate_context_size()

        # Выбираем уровень
        if context_size > 4000:
            level = PromptLevel.MINIMAL
        elif context_size > 2000:
            level = PromptLevel.COMPACT
        else:
            level = PromptLevel.FULL

        # Загружаем промпт
        agent = self.get_specialized_agent(task_type)
        return agent.get_system_prompt(level)
```

### 2. Мониторинг использования
Добавить метрики для отслеживания:
- Как часто используется каждый уровень
- Влияние уровня на качество ответов
- Экономия токенов в runtime

### 3. A/B тестирование
Сравнить качество работы агентов на разных уровнях:
- MINIMAL vs COMPACT vs FULL
- Определить оптимальный уровень для каждого типа задач

### 4. Создание промптов для GeneralAgent
Добавить 3 уровня для общего агента:
- `prompts/general_minimal.txt`
- `prompts/general_compact.txt`
- `prompts/general_full.txt`

---

## 🔍 Тестирование

### Тестовый скрипт
Создан скрипт для тестирования: `tests/test_prompts_simple.py`

**Результаты:**
```
SHOPPING:
  MINIMAL ≤ 300 токенов: ✅ (фактически 230)
  COMPACT ≤ 600 токенов: ✅ (фактически 509)

EMAIL:
  MINIMAL ≤ 250 токенов: ✅ (фактически 191)
  COMPACT ≤ 500 токенов: ✅ (фактически 379)

JOB_SEARCH:
  MINIMAL ≤ 250 токенов: ✅ (фактически 142)
  COMPACT ≤ 600 токенов: ✅ (фактически 364)

✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО
```

---

## 📦 Коммит

**Хеш:** `3dd72ac`

**Сообщение:**
```
feat: Add multi-level prompt system for specialized agents

Реализована система управления промптами с 3 уровнями детализации:
- MINIMAL (~150-250 токенов) - только критичные инструкции
- COMPACT (~350-500 токенов) - основные инструкции без примеров
- FULL (~900-3100 токенов) - полная база знаний

Изменения:
- Создана директория prompts/ с 9 файлами промптов
- Добавлен метод PromptManager.load_prompt(agent_name, level)
- Обновлен SpecializedAgent для поддержки уровней промптов
- Добавлено кеширование промптов
- Автоматическое добавление язык-якоря

Результаты:
- ShoppingAgent MINIMAL: 230 токенов (экономия 92.6%)
- EmailAgent MINIMAL: 191 токенов (экономия 79.1%)
- JobSearchAgent MINIMAL: 142 токенов (экономия 87.0%)

Тестирование: Все критерии успеха выполнены ✅

```

---

## ✅ Итоги

**Статус:** Все задачи выполнены успешно

**Достигнуто:**
- ✅ Создано 9 файлов промптов (3 уровня × 3 агента)
- ✅ Модифицирован PromptManager для загрузки по уровням
- ✅ Обновлен SpecializedAgent с поддержкой уровней
- ✅ Добавлено кеширование промптов
- ✅ Все тесты пройдены
- ✅ Критерии экономии токенов выполнены
- ✅ Коммит создан и готов к push

**Экономия:**
- ShoppingAgent: до 92.6%
- EmailAgent: до 79.1%
- JobSearchAgent: до 87.0%

---

**Конец отчета Сессии 2**
