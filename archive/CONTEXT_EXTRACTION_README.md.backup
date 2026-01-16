# Context Extraction Pattern - Quick Start

## Что это?

Автоматическое извлечение критичной информации из диалога с интеллектуальной подачей контекста.

## Проблема → Решение

### До ❌
```python
# DialogueManager хранил user_restrictions
self.user_restrictions = {"allergies": [], ...}  # Не его ответственность!

# Передавал везде
context += self._format_user_restrictions()  # На КАЖДОМ действии!

# Пользователь должен был сказать явно
"У меня аллергия на..."  # Навязчивые вопросы
```

### После ✅
```python
# ContextExtractor - отдельный класс
self.context_extractor = ContextExtractor(llm_client)

# Автоматическое извлечение
await self.context_extractor.extract_from_turn(user_msg, agent_response)

# Только релевантный контекст
context += self.context_extractor.get_context_for_action(action_type)
```

## Как работает?

```
User: "Закажи пиццу без морепродуктов"
  ↓
LLM автоматически извлекает:
  {"dietary_restrictions": "аллергия на морепродукты"}
  ↓
При click_by_text → передает: "⚠️ ОГРАНИЧЕНИЯ: аллергия на морепродукты"
При scroll → передает: "" (не релевантно)
```

## Использование

### 1. Инициализация
```python
from src.agent.context_extractor import ContextExtractor

self.context_extractor = ContextExtractor(self.agent.client)
```

### 2. Извлечение контекста
```python
# После каждого раунда диалога
response = self.agent.chat(user_input)
await self.context_extractor.extract_from_turn(user_input, response)
```

### 3. Использование контекста
```python
# При выполнении действий
def _format_action_result(self, result, action):
    context = f"Действие: {action['action']}\n..."

    # Добавляем ТОЛЬКО релевантный контекст
    relevant_context = self.context_extractor.get_context_for_action(
        action['action']
    )
    if relevant_context:
        context += f"\n{relevant_context}"

    return context
```

## Типы контекста

Поддерживаемые типы:
- `dietary_restrictions` - аллергии, веганство, религиозные ограничения
- `people_count` - количество людей
- `budget` - бюджет
- `location` - город
- `delivery_address` - адрес доставки
- `delivery_time` - время доставки

## Релевантность контекста

| Контекст | Релевантен для действий |
|----------|------------------------|
| dietary_restrictions | click_by_text, get_modal_text, get_page_text |
| people_count | click_by_text, get_modal_text |
| budget | click_by_text, get_page_text |
| location | navigate, type_text |

## Пример

```python
# Диалог
User: "Закажи пиццу на 4 человек, я не ем лактозу"
Agent: "Буду искать безлактозную пиццу"

# Автоматически извлечено:
{
  "dietary_restrictions": "без лактозы",
  "people_count": 4
}

# При click_by_text("Четыре сыра"):
⚠️ ВАЖНАЯ ИНФОРМАЦИЯ:
🚨 ОГРАНИЧЕНИЯ: без лактозы
👥 Количество человек: 4

# При scroll():
(пустой - не релевантно)
```

## API

### ContextExtractor

```python
class ContextExtractor:
    async def extract_from_turn(user_msg: str, agent_response: str)
        """Извлечь контекст из раунда диалога"""

    def get_context_for_action(action_type: str) -> str
        """Получить релевантный контекст для действия"""

    def get_all_context() -> Dict[str, Any]
        """Получить весь контекст"""

    def clear_context()
        """Очистить контекст"""

    def has_context() -> bool
        """Проверить наличие контекста"""
```

## Преимущества

✅ **Автоматическое** - LLM сам определяет что важно
✅ **Умное** - передает только релевантный контекст
✅ **Чистое** - отдельный класс с четкой ответственностью
✅ **Расширяемое** - легко добавить новые типы контекста

## Подробная документация

См. [CONTEXT_EXTRACTION_PATTERN.md](docs/CONTEXT_EXTRACTION_PATTERN.md)

## Файлы

- `src/agent/context_extractor.py` - реализация
- `src/dialogue_manager.py` - интеграция
- `tests/unit/test_context_extractor.py` - тесты
- `docs/CONTEXT_EXTRACTION_PATTERN.md` - полная документация
