# 🚀 Quick Start: Интеллектуальная система выбора контекста

## ⚡ Быстрый старт (30 секунд)

```python
from src.agent.ai_agent import AIAgent
from src.agent.knowledge_base import KnowledgeBase
from src.agent.specialized_agents import ShoppingAgent

# 1. Создаём агента
agent = AIAgent()

# 2. Подключаем базу знаний (для оптимизации)
kb = KnowledgeBase(agent.client, "data/knowledge_base.json")
agent.knowledge_base = kb

# 3. Устанавливаем тип задачи
agent.set_task_type("shopping")

# 4. Добавляем системный промпт
agent.add_system_prompt()

# 5. Используем со specialized agent
shopping_agent = ShoppingAgent()
response = agent.chat("Хочу пиццу с доставкой", specialized_agent=shopping_agent)

# 6. Проверяем статистику
stats = agent.get_token_usage_stats()
print(f"✅ Уровень: {stats['context_level']} / {stats['prompt_level']}")
print(f"✅ Экономия: {stats['kb_savings_percent']}%")
```

## 📊 Проверка статистики

```python
stats = agent.get_token_usage_stats()

print(f"Модель: {stats['model']}")
print(f"Использовано: {stats['used_tokens']}/{stats['safe_limit']} токенов")
print(f"Уровень контекста: {stats['context_level']}")
print(f"Уровень промпта: {stats['prompt_level']}")
print(f"Экономия: {stats['kb_savings_percent']}%")
```

## 🔄 Смена типа задачи

```python
# Заказ еды
agent.set_task_type("shopping")
shopping_agent = ShoppingAgent()
agent.chat("Закажи пиццу", specialized_agent=shopping_agent)

# Поиск работы
agent.set_task_type("job_search")
job_agent = JobSearchAgent()
agent.chat("Найди вакансии Python", specialized_agent=job_agent)

# Работа с почтой
agent.set_task_type("email")
email_agent = EmailAgent()
agent.chat("Удали спам", specialized_agent=email_agent)
```

## 🧪 Тестирование

```bash
# Проверка структуры кода (без API)
python3 verify_implementation.py

# Полное тестирование (требует API ключ)
python3 test_context_optimization.py
```

## 📚 Подробная документация

Смотри [CONTEXT_OPTIMIZATION_REPORT.md](CONTEXT_OPTIMIZATION_REPORT.md) для детального описания всех компонентов.

## 🎯 Ожидаемые результаты

✅ Автоматический выбор уровня контекста (FULL → COMPACT → MINIMAL)
✅ Экономия токенов 50-70%
✅ Снижение rate limit на 80-90%
✅ Кеширование промптов
✅ Graceful degradation при переполнении контекста

## ❓ Часто задаваемые вопросы

### Q: Работает ли без knowledge_base?

A: Да, но без оптимизации. Рекомендуется всегда подключать KB.

### Q: Обязательно ли передавать specialized_agent?

A: Нет, опционально. Без него будет использоваться general agent промпт.

### Q: Как узнать текущий уровень контекста?

A: Используй `agent.get_token_usage_stats()['context_level']`

### Q: Что делать если rate limit всё ещё происходит?

A: Проверь:
- Подключена ли knowledge_base
- Установлен ли task_type
- Передаётся ли specialized_agent в chat()

## 🐛 Устранение проблем

### Проблема: "Атрибут knowledge_base не найден"

```python
# ❌ Неправильно
agent = AIAgent()
agent.chat("Hello")  # knowledge_base не установлен

# ✅ Правильно
agent = AIAgent()
agent.knowledge_base = KnowledgeBase(agent.client, "data/knowledge_base.json")
agent.chat("Hello")
```

### Проблема: "Кеш промпта не инвалидируется"

```python
# Явно сбросить кеш при смене типа задачи
agent.set_task_type("shopping")  # Кеш автоматически сбрасывается

# Или вручную
agent._cached_prompt_level = None
agent._cached_system_prompt = None
```

### Проблема: "Уровень всегда MINIMAL"

Это нормально при переполненной истории. Сбрось историю:

```python
agent.reset_conversation()
```

## 📞 Поддержка

Для вопросов и багов создавай issue в GitHub.

---

**Версия:** 1.0
**Дата:** 2026-01-16
