# 🧪 СЕССИЯ 5: Тестирование системы оптимизации контекста

## Контекст проекта

Я работаю над проектом `/home/gleckus/projects/ai-browser-agent`

## Что было сделано ранее

### Сессии 1-4: Полная реализация системы оптимизации контекста

**Сессия 1 (KnowledgeBase):**
- ✅ 3-уровневая система (MINIMAL ~100т, COMPACT ~300т, FULL ~800т)
- ✅ Локализация по task_type (shopping/email/job_search)
- ✅ `get_context_summary(level, task_type)` и `estimate_tokens()`
- ✅ Файл: `src/agent/knowledge_base.py`

**Сессия 2 (Промпты):**
- ✅ 9 файлов промптов в `prompts/` (3 агента × 3 уровня)
- ✅ Shopping: MINIMAL 230т, COMPACT 509т, FULL 3103т
- ✅ Email: MINIMAL 191т, COMPACT 379т, FULL 912т
- ✅ JobSearch: MINIMAL 142т, COMPACT 364т, FULL 1092т
- ✅ `SpecializedAgent.get_system_prompt(level)` с кешированием

**Сессия 3 (AIAgent):**
- ✅ `_select_context_level()` - автоматический выбор уровня
- ✅ `_prepare_context_for_request()` - подготовка контекста
- ✅ `set_task_type()` - установка типа задачи
- ✅ `get_token_usage_stats()` - мониторинг
- ✅ Graceful degradation (FULL → COMPACT → MINIMAL)
- ✅ Файл: `src/agent/ai_agent.py`

**Сессия 4 (Документация):**
- ✅ `docs/CONTEXT_OPTIMIZATION.md` - полная документация
- ✅ `docs/CONTEXT_OPTIMIZATION_QUICKSTART.md` - быстрый старт
- ✅ `README.md` - обновлён раздел "Оптимизация контекста"
- ✅ Интеграция с DialogueManager подтверждена

## Проблема сейчас

Система полностью реализована и задокументирована, но **не протестирована автоматическими тестами**.

Необходимо убедиться что:
1. Все компоненты работают корректно
2. Экономия токенов действительно достигает 50-70%
3. Graceful degradation работает (FULL → COMPACT → MINIMAL)
4. Локализация по task_type фильтрует контекст правильно
5. Кеширование промптов работает
6. Интеграция с DialogueManager не сломана

## 🎯 Задачи этой сессии

Создать и запустить автоматические тесты для проверки всей системы оптимизации контекста.

## 📝 Что нужно сделать

### 1. Создать unit тесты

**Файл:** `tests/unit/test_context_optimization.py`

Создай файл с тестами для следующих компонентов:

#### 1.1 Тесты для KnowledgeBase

```python
import pytest
from src.agent.knowledge_base import KnowledgeBase, ContextLevel

class TestKnowledgeBaseOptimization:
    """Тесты для KnowledgeBase с уровнями контекста"""

    def test_context_level_minimal(self):
        """MINIMAL должен возвращать ~100 токенов"""
        kb = KnowledgeBase(llm_client=None, storage_path="data/knowledge_base.json")

        tokens = kb.estimate_tokens(ContextLevel.MINIMAL)
        context = kb.get_context_summary(ContextLevel.MINIMAL)

        # Проверки
        assert tokens <= 150, f"MINIMAL должен быть ≤150 токенов, получено {tokens}"
        assert "русском языке" in context.lower(), "Должен быть язык-якорь"
        assert len(context) > 0, "Контекст не должен быть пустым"

        print(f"✅ MINIMAL: {tokens} токенов")

    def test_context_level_compact(self):
        """COMPACT должен возвращать ~300 токенов"""
        kb = KnowledgeBase(llm_client=None, storage_path="data/knowledge_base.json")

        tokens = kb.estimate_tokens(ContextLevel.COMPACT)

        assert 200 <= tokens <= 500, f"COMPACT должен быть 200-500 токенов, получено {tokens}"

        print(f"✅ COMPACT: {tokens} токенов")

    def test_context_level_full(self):
        """FULL должен возвращать весь контекст"""
        kb = KnowledgeBase(llm_client=None, storage_path="data/knowledge_base.json")

        tokens = kb.estimate_tokens(ContextLevel.FULL)

        assert tokens >= 400, f"FULL должен быть ≥400 токенов, получено {tokens}"

        print(f"✅ FULL: {tokens} токенов")

    def test_graceful_degradation(self):
        """Проверка что MINIMAL < COMPACT < FULL"""
        kb = KnowledgeBase(llm_client=None, storage_path="data/knowledge_base.json")

        minimal = kb.estimate_tokens(ContextLevel.MINIMAL)
        compact = kb.estimate_tokens(ContextLevel.COMPACT)
        full = kb.estimate_tokens(ContextLevel.FULL)

        assert minimal < compact, f"MINIMAL ({minimal}) должен быть < COMPACT ({compact})"
        assert compact < full, f"COMPACT ({compact}) должен быть < FULL ({full})"

        print(f"✅ Degradation: MINIMAL={minimal}т < COMPACT={compact}т < FULL={full}т")

    def test_task_type_localization_shopping(self):
        """Локализация для shopping должна фильтровать контекст"""
        kb = KnowledgeBase(llm_client=None, storage_path="data/knowledge_base.json")

        # Добавляем тестовые данные
        kb.knowledge["user_info"]["preferences"] = ["пицца", "Python", "Docker"]

        # Shopping должен взять только еду
        shopping_context = kb.get_context_summary(ContextLevel.COMPACT, "shopping")

        # НЕ строгая проверка - может не содержать если структура другая
        # Просто проверим что контекст генерируется
        assert len(shopping_context) > 0, "Shopping контекст не должен быть пустым"
        assert "русском языке" in shopping_context.lower(), "Должен быть язык-якорь"

        print(f"✅ Shopping локализация работает")

    def test_language_anchor_all_levels(self):
        """Язык-якорь должен быть во всех уровнях"""
        kb = KnowledgeBase(llm_client=None, storage_path="data/knowledge_base.json")

        for level in [ContextLevel.MINIMAL, ContextLevel.COMPACT, ContextLevel.FULL]:
            context = kb.get_context_summary(level)
            assert "русском языке" in context.lower(), \
                f"Язык-якорь отсутствует в {level.value}"

        print("✅ Язык-якорь присутствует во всех уровнях")
```

#### 1.2 Тесты для PromptManager

```python
from src.prompts.prompt_manager import PromptManager, PromptLevel

class TestPromptOptimization:
    """Тесты для системы промптов"""

    def test_prompt_loading_shopping(self):
        """Загрузка промптов для shopping агента"""
        pm = PromptManager()

        minimal = pm.load_prompt("shopping", PromptLevel.MINIMAL)
        compact = pm.load_prompt("shopping", PromptLevel.COMPACT)
        full = pm.load_prompt("shopping", PromptLevel.FULL)

        # Оценка токенов
        minimal_tokens = pm.estimate_prompt_tokens(minimal)
        compact_tokens = pm.estimate_prompt_tokens(compact)
        full_tokens = pm.estimate_prompt_tokens(full)

        # Проверки (с запасом 20%)
        assert minimal_tokens <= 350, f"Shopping MINIMAL: {minimal_tokens}т > 350т"
        assert compact_tokens <= 700, f"Shopping COMPACT: {compact_tokens}т > 700т"
        assert full_tokens >= 1000, f"Shopping FULL: {full_tokens}т < 1000т"

        # Проверка язык-якоря
        for prompt in [minimal, compact, full]:
            assert "русском языке" in prompt.lower(), "Язык-якорь отсутствует"

        print(f"✅ Shopping промпты: {minimal_tokens}т / {compact_tokens}т / {full_tokens}т")

    def test_prompt_loading_email(self):
        """Загрузка промптов для email агента"""
        pm = PromptManager()

        minimal = pm.load_prompt("email", PromptLevel.MINIMAL)
        compact = pm.load_prompt("email", PromptLevel.COMPACT)
        full = pm.load_prompt("email", PromptLevel.FULL)

        minimal_tokens = pm.estimate_prompt_tokens(minimal)
        compact_tokens = pm.estimate_prompt_tokens(compact)
        full_tokens = pm.estimate_prompt_tokens(full)

        assert minimal_tokens <= 300, f"Email MINIMAL: {minimal_tokens}т > 300т"
        assert compact_tokens <= 600, f"Email COMPACT: {compact_tokens}т > 600т"

        print(f"✅ Email промпты: {minimal_tokens}т / {compact_tokens}т / {full_tokens}т")

    def test_prompt_loading_job_search(self):
        """Загрузка промптов для job_search агента"""
        pm = PromptManager()

        minimal = pm.load_prompt("job_search", PromptLevel.MINIMAL)
        compact = pm.load_prompt("job_search", PromptLevel.COMPACT)
        full = pm.load_prompt("job_search", PromptLevel.FULL)

        minimal_tokens = pm.estimate_prompt_tokens(minimal)
        compact_tokens = pm.estimate_prompt_tokens(compact)
        full_tokens = pm.estimate_prompt_tokens(full)

        assert minimal_tokens <= 250, f"JobSearch MINIMAL: {minimal_tokens}т > 250т"
        assert compact_tokens <= 600, f"JobSearch COMPACT: {compact_tokens}т > 600т"

        print(f"✅ JobSearch промпты: {minimal_tokens}т / {compact_tokens}т / {full_tokens}т")
```

#### 1.3 Тесты для SpecializedAgent

```python
from src.agent.specialized_agents import ShoppingAgent, EmailAgent, JobSearchAgent

class TestSpecializedAgentCaching:
    """Тесты для кеширования в SpecializedAgent"""

    def test_shopping_agent_caching(self):
        """Кеширование промптов в ShoppingAgent"""
        agent = ShoppingAgent()

        # Первая загрузка
        prompt1 = agent.get_system_prompt(PromptLevel.COMPACT)
        assert agent._cached_prompt is not None, "Кеш должен быть установлен"
        assert agent._cached_level == PromptLevel.COMPACT

        # Вторая загрузка (должна вернуть кешированный)
        prompt2 = agent.get_system_prompt(PromptLevel.COMPACT)
        assert prompt1 == prompt2, "Должен вернуть тот же промпт"

        print("✅ ShoppingAgent кеширование работает")

    def test_cache_invalidation_on_level_change(self):
        """Смена уровня должна инвалидировать кеш"""
        agent = EmailAgent()

        # Загружаем COMPACT
        prompt_compact = agent.get_system_prompt(PromptLevel.COMPACT)
        assert agent._cached_level == PromptLevel.COMPACT

        # Загружаем MINIMAL - кеш должен обновиться
        prompt_minimal = agent.get_system_prompt(PromptLevel.MINIMAL)
        assert agent._cached_level == PromptLevel.MINIMAL
        assert prompt_compact != prompt_minimal, "Промпты должны отличаться"

        print("✅ Инвалидация кеша при смене уровня работает")
```

#### 1.4 Тесты для AIAgent

```python
from src.agent.ai_agent import AIAgent
from src.agent.knowledge_base import KnowledgeBase, ContextLevel

class TestAIAgentOptimization:
    """Тесты для AIAgent с оптимизацией"""

    def test_set_task_type_invalidates_cache(self):
        """Смена типа задачи должна инвалидировать кеш"""
        agent = AIAgent()
        agent._cached_prompt_level = PromptLevel.COMPACT
        agent._cached_system_prompt = "cached"

        # Меняем тип
        agent.set_task_type("shopping")

        assert agent.task_type == "shopping"
        assert agent._cached_prompt_level is None, "Кеш уровня должен быть сброшен"
        assert agent._cached_system_prompt is None, "Кеш промпта должен быть сброшен"

        print("✅ set_task_type() инвалидирует кеш")

    def test_token_usage_stats_structure(self):
        """Статистика должна возвращать корректные поля"""
        agent = AIAgent()
        agent.knowledge_base = KnowledgeBase(None, "data/knowledge_base.json")

        stats = agent.get_token_usage_stats()

        # Проверяем наличие всех полей
        required_fields = [
            'model', 'model_limit', 'safe_limit', 'used_tokens',
            'available_tokens', 'usage_percent', 'context_level',
            'prompt_level', 'kb_savings_percent', 'task_type'
        ]

        for field in required_fields:
            assert field in stats, f"Поле '{field}' отсутствует в статистике"

        # Проверяем типы
        assert isinstance(stats['model'], str)
        assert isinstance(stats['model_limit'], int)
        assert isinstance(stats['used_tokens'], int)
        assert stats['context_level'] in ['minimal', 'compact', 'full']

        print("✅ get_token_usage_stats() возвращает корректную структуру")

    def test_context_level_selection_logic(self):
        """Проверка логики выбора уровня контекста"""
        agent = AIAgent()
        agent.knowledge_base = KnowledgeBase(agent.client, "data/knowledge_base.json")

        # Пустая история - должен быть FULL или COMPACT
        context_level, prompt_level = agent._select_context_level(
            "llama-3.3-70b-versatile",
            None
        )
        assert context_level in [ContextLevel.FULL, ContextLevel.COMPACT], \
            f"При пустой истории ожидался FULL или COMPACT, получен {context_level}"

        print(f"✅ Выбор уровня: пустая история → {context_level.value}")

        # Заполняем историю большим количеством сообщений
        for i in range(30):
            agent.conversation_history.append({
                "role": "user",
                "content": f"Тестовое сообщение номер {i}" * 50  # Длинное сообщение
            })

        # Должен выбрать MINIMAL или COMPACT
        context_level2, prompt_level2 = agent._select_context_level(
            "llama-3.3-70b-versatile",
            None
        )
        assert context_level2 in [ContextLevel.MINIMAL, ContextLevel.COMPACT], \
            f"При полной истории ожидался MINIMAL или COMPACT, получен {context_level2}"

        print(f"✅ Выбор уровня: полная история → {context_level2.value}")
```

### 2. Создать интеграционный тест

**Файл:** `tests/integration/test_optimization_integration.py`

```python
"""
Интеграционный тест: проверка работы всей системы оптимизации
"""
import pytest
from src.agent.ai_agent import AIAgent
from src.agent.knowledge_base import KnowledgeBase, ContextLevel
from src.agent.specialized_agents import ShoppingAgent
from src.prompts.prompt_manager import PromptLevel

class TestOptimizationIntegration:
    """Интеграционные тесты всей системы"""

    def test_full_optimization_flow(self):
        """Тест полного флоу оптимизации"""
        # 1. Создаём агента
        agent = AIAgent()
        kb = KnowledgeBase(agent.client, "data/knowledge_base.json")
        agent.knowledge_base = kb

        # 2. Устанавливаем тип задачи
        agent.set_task_type("shopping")

        # 3. Получаем статистику (начальное состояние)
        stats_initial = agent.get_token_usage_stats()

        assert stats_initial['task_type'] == 'shopping'
        assert stats_initial['context_level'] in ['minimal', 'compact', 'full']
        assert stats_initial['prompt_level'] in ['minimal', 'compact', 'full']

        print(f"✅ Начальное состояние:")
        print(f"   Контекст: {stats_initial['context_level']}")
        print(f"   Промпт: {stats_initial['prompt_level']}")
        print(f"   Использовано: {stats_initial['used_tokens']} токенов")

        # 4. Проверяем что экономия работает
        full_kb = kb.estimate_tokens(ContextLevel.FULL, "shopping")
        current_kb = kb.estimate_tokens(
            ContextLevel[stats_initial['context_level'].upper()],
            "shopping"
        )

        savings_percent = ((full_kb - current_kb) / full_kb * 100) if full_kb > 0 else 0

        print(f"   Экономия KB: {savings_percent:.1f}%")
        assert savings_percent >= 0, "Экономия не может быть отрицательной"

    def test_task_type_switch(self):
        """Тест смены типа задачи"""
        agent = AIAgent()
        kb = KnowledgeBase(agent.client, "data/knowledge_base.json")
        agent.knowledge_base = kb

        # Shopping
        agent.set_task_type("shopping")
        stats1 = agent.get_token_usage_stats()
        assert stats1['task_type'] == 'shopping'

        # Email
        agent.set_task_type("email")
        stats2 = agent.get_token_usage_stats()
        assert stats2['task_type'] == 'email'

        # Job Search
        agent.set_task_type("job_search")
        stats3 = agent.get_token_usage_stats()
        assert stats3['task_type'] == 'job_search'

        print("✅ Смена типа задачи работает корректно")

    def test_savings_calculation(self):
        """Проверка расчёта экономии токенов"""
        agent = AIAgent()
        kb = KnowledgeBase(agent.client, "data/knowledge_base.json")
        agent.knowledge_base = kb

        # Сравниваем разные уровни
        minimal_tokens = kb.estimate_tokens(ContextLevel.MINIMAL)
        full_tokens = kb.estimate_tokens(ContextLevel.FULL)

        savings = ((full_tokens - minimal_tokens) / full_tokens) * 100 if full_tokens > 0 else 0

        print(f"✅ Экономия MINIMAL vs FULL: {savings:.1f}%")
        print(f"   MINIMAL: {minimal_tokens}т")
        print(f"   FULL: {full_tokens}т")

        # Экономия должна быть хотя бы 30%
        assert savings >= 30, f"Ожидалась экономия ≥30%, получено {savings:.1f}%"
```

### 3. Создать benchmark тест

**Файл:** `tests/benchmark/test_token_savings.py`

```python
"""
Benchmark тест: измерение экономии токенов в реальных сценариях
"""
import pytest
from src.agent.ai_agent import AIAgent
from src.agent.knowledge_base import KnowledgeBase, ContextLevel
from src.agent.specialized_agents import ShoppingAgent, EmailAgent, JobSearchAgent
from src.prompts.prompt_manager import PromptLevel

class TestTokenSavingsBenchmark:
    """Benchmark тесты для измерения экономии"""

    def test_shopping_agent_savings(self):
        """Измерение экономии для ShoppingAgent"""
        kb = KnowledgeBase(None, "data/knowledge_base.json")
        agent = ShoppingAgent()

        # KB токены
        kb_minimal = kb.estimate_tokens(ContextLevel.MINIMAL, "shopping")
        kb_compact = kb.estimate_tokens(ContextLevel.COMPACT, "shopping")
        kb_full = kb.estimate_tokens(ContextLevel.FULL, "shopping")

        # Промпт токены
        prompt_minimal = agent.get_system_prompt(PromptLevel.MINIMAL)
        prompt_compact = agent.get_system_prompt(PromptLevel.COMPACT)
        prompt_full = agent.get_system_prompt(PromptLevel.FULL)

        from src.prompts.prompt_manager import PromptManager
        pm = PromptManager()

        p_minimal = pm.estimate_prompt_tokens(prompt_minimal)
        p_compact = pm.estimate_prompt_tokens(prompt_compact)
        p_full = pm.estimate_prompt_tokens(prompt_full)

        # Общие токены
        total_minimal = kb_minimal + p_minimal
        total_compact = kb_compact + p_compact
        total_full = kb_full + p_full

        # Экономия
        savings_minimal = ((total_full - total_minimal) / total_full * 100)
        savings_compact = ((total_full - total_compact) / total_full * 100)

        print("\n" + "="*60)
        print("📊 SHOPPING AGENT - ЭКОНОМИЯ ТОКЕНОВ")
        print("="*60)
        print(f"MINIMAL: {total_minimal}т (экономия {savings_minimal:.1f}%)")
        print(f"COMPACT: {total_compact}т (экономия {savings_compact:.1f}%)")
        print(f"FULL:    {total_full}т (базовый)")
        print("="*60)

        # Проверяем что экономия достигается
        assert savings_minimal >= 40, f"MINIMAL экономия <40%: {savings_minimal:.1f}%"
        assert savings_compact >= 20, f"COMPACT экономия <20%: {savings_compact:.1f}%"

    def test_all_agents_comparison(self):
        """Сравнение экономии для всех агентов"""
        kb = KnowledgeBase(None, "data/knowledge_base.json")

        agents = {
            "Shopping": (ShoppingAgent(), "shopping"),
            "Email": (EmailAgent(), "email"),
            "JobSearch": (JobSearchAgent(), "job_search")
        }

        from src.prompts.prompt_manager import PromptManager
        pm = PromptManager()

        print("\n" + "="*60)
        print("📊 СРАВНЕНИЕ ЭКОНОМИИ ПО АГЕНТАМ")
        print("="*60)

        for name, (agent, task_type) in agents.items():
            kb_minimal = kb.estimate_tokens(ContextLevel.MINIMAL, task_type)
            kb_full = kb.estimate_tokens(ContextLevel.FULL, task_type)

            p_minimal_txt = agent.get_system_prompt(PromptLevel.MINIMAL)
            p_full_txt = agent.get_system_prompt(PromptLevel.FULL)

            p_minimal = pm.estimate_prompt_tokens(p_minimal_txt)
            p_full = pm.estimate_prompt_tokens(p_full_txt)

            total_minimal = kb_minimal + p_minimal
            total_full = kb_full + p_full

            savings = ((total_full - total_minimal) / total_full * 100)

            print(f"{name:12} | MINIMAL: {total_minimal:4}т | FULL: {total_full:4}т | Экономия: {savings:5.1f}%")

        print("="*60)
```

### 4. Запустить все тесты

После создания тестов выполни:

```bash
# Переход в директорию проекта
cd /home/gleckus/projects/ai-browser-agent

# Установка pytest (если нет)
pip install pytest pytest-asyncio

# Запуск unit тестов
pytest tests/unit/test_context_optimization.py -v

# Запуск интеграционных тестов
pytest tests/integration/test_optimization_integration.py -v

# Запуск benchmark
pytest tests/benchmark/test_token_savings.py -v -s

# Запуск всех тестов оптимизации
pytest tests/ -k "optimization or savings" -v
```

### 5. Создать отчёт о результатах тестирования

**Файл:** `docs/TESTING_RESULTS.md`

Создай markdown отчёт с результатами:

```markdown
# 🧪 Результаты тестирования системы оптимизации контекста

## Дата: [дата запуска]

## Выполненные тесты

### Unit тесты

#### KnowledgeBase
- ✅/❌ test_context_level_minimal
- ✅/❌ test_context_level_compact
- ✅/❌ test_context_level_full
- ✅/❌ test_graceful_degradation
- ✅/❌ test_task_type_localization
- ✅/❌ test_language_anchor_all_levels

#### PromptManager
- ✅/❌ test_prompt_loading_shopping
- ✅/❌ test_prompt_loading_email
- ✅/❌ test_prompt_loading_job_search

#### SpecializedAgent
- ✅/❌ test_shopping_agent_caching
- ✅/❌ test_cache_invalidation_on_level_change

#### AIAgent
- ✅/❌ test_set_task_type_invalidates_cache
- ✅/❌ test_token_usage_stats_structure
- ✅/❌ test_context_level_selection_logic

### Интеграционные тесты
- ✅/❌ test_full_optimization_flow
- ✅/❌ test_task_type_switch
- ✅/❌ test_savings_calculation

### Benchmark тесты
- ✅/❌ test_shopping_agent_savings
- ✅/❌ test_all_agents_comparison

## Результаты экономии токенов

[Скопируй вывод benchmark тестов сюда]

## Найденные проблемы

[Опиши любые проблемы или неожиданные результаты]

## Рекомендации

[Что нужно исправить или улучшить]

## Заключение

[Общий вывод о готовности системы]
```

## ✅ Критерии успеха

1. ✅ Созданы unit тесты для всех компонентов (10+ тестов)
2. ✅ Созданы интеграционные тесты (3+ теста)
3. ✅ Создан benchmark для измерения экономии
4. ✅ Все тесты проходят успешно (или задокументированы причины провала)
5. ✅ Подтверждена экономия токенов ≥40% для MINIMAL
6. ✅ Подтверждена экономия токенов ≥20% для COMPACT
7. ✅ Graceful degradation работает (MINIMAL < COMPACT < FULL)
8. ✅ Локализация по task_type работает
9. ✅ Кеширование промптов работает
10. ✅ Создан отчёт `docs/TESTING_RESULTS.md`

## 📊 Ожидаемые результаты

### Экономия токенов

| Агент | MINIMAL экономия | COMPACT экономия |
|-------|------------------|------------------|
| Shopping | ≥40% | ≥20% |
| Email | ≥35% | ≥15% |
| JobSearch | ≥35% | ≥15% |

### Уровни контекста

- MINIMAL: ~300 токенов (KB + промпт)
- COMPACT: ~800 токенов
- FULL: ~4000 токенов

### Успешность тестов

Ожидается 100% прохождение тестов. Если какие-то тесты падают:
1. Задокументируй причину в `TESTING_RESULTS.md`
2. Предложи fix или объясни почему это ожидаемое поведение

## 🎯 Важные замечания

1. **Не требуется API ключ** для большинства unit тестов (используй `llm_client=None`)
2. **Benchmark тесты** должны выводить детальную статистику (используй `-s` флаг pytest)
3. **Интеграционные тесты** могут требовать API ключ - пропускай их если его нет
4. **Проверяй с запасом**: токены могут варьироваться ±10-20%
5. **Документируй всё**: каждый тест должен выводить результат в консоль

## 📁 Структура файлов для создания

```
tests/
├── unit/
│   └── test_context_optimization.py   # Unit тесты
├── integration/
│   └── test_optimization_integration.py  # Интеграционные тесты
└── benchmark/
    └── test_token_savings.py          # Benchmark тесты

docs/
└── TESTING_RESULTS.md                 # Отчёт о результатах
```

## 🚀 Начни работу

1. Создай директорию `tests/benchmark/` если её нет
2. Создай файл `tests/unit/test_context_optimization.py` со всеми unit тестами
3. Создай файл `tests/integration/test_optimization_integration.py`
4. Создай файл `tests/benchmark/test_token_savings.py`
5. Запусти unit тесты: `pytest tests/unit/test_context_optimization.py -v`
6. Запусти интеграционные тесты: `pytest tests/integration/test_optimization_integration.py -v`
7. Запусти benchmark: `pytest tests/benchmark/test_token_savings.py -v -s`
8. Создай отчёт `docs/TESTING_RESULTS.md` с результатами
9. Закоммить все изменения

После завершения сообщи:
- Сколько тестов прошло/провалилось
- Какая экономия токенов подтверждена
- Какие проблемы найдены (если есть)
- Рекомендации по улучшению

Удачи! 🎉
