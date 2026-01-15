# Context Extraction Pattern

## Проблема

Раньше в `DialogueManager` было хранилище `user_restrictions` которое:
- ❌ Не его ответственность (нарушение Single Responsibility)
- ❌ Передавалось при КАЖДОМ действии (избыточно)
- ❌ Требовало ручного управления (пользователь сам должен был сказать об аллергиях)

```python
# Старый подход ❌
self.user_restrictions = {
    "allergies": [],
    "dislikes": [],
    "preferences": []
}

# Передается ВЕЗДЕ
context += self._format_user_restrictions()  # На КАЖДОМ действии!
```

## Решение: Context Extraction Pattern

### Философия

**LLM сам определяет что важно, мы только помогаем не забыть**

- ✅ Автоматическое извлечение критичной информации
- ✅ Контекстно-зависимая подача (не везде нужно)
- ✅ Чистая архитектура (отдельная ответственность)
- ✅ Расширяемость (легко добавить новые типы контекста)

### Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                    DialogueManager                          │
│                                                             │
│  1. User: "Хочу пиццу без лактозы"                         │
│  2. Agent: "Буду искать безлактозную пиццу"                │
│                                                             │
│  3. extract_from_turn(user_msg, agent_response)            │
│     └──> ContextExtractor анализирует диалог               │
│          └──> LLM извлекает: {"dietary_restrictions":...}  │
│                                                             │
│  4. При действии click_by_text:                            │
│     get_context_for_action("click_by_text")                │
│     └──> Возвращает ТОЛЬКО релевантный контекст            │
│          "⚠️ ОГРАНИЧЕНИЯ: без лактозы"                     │
│                                                             │
│  5. При действии scroll:                                   │
│     get_context_for_action("scroll")                       │
│     └──> Возвращает "" (не релевантно)                     │
└─────────────────────────────────────────────────────────────┘
```

## Реализация

### 1. ContextExtractor класс

```python
class ContextExtractor:
    """
    Извлекает важный контекст из разговора автоматически
    """

    # Маппинг: какой контекст важен для каких действий
    CONTEXT_RELEVANCE = {
        "dietary_restrictions": ["click_by_text", "get_modal_text", "get_page_text"],
        "people_count": ["click_by_text", "get_modal_text"],
        "budget": ["click_by_text", "get_page_text"],
        "location": ["navigate", "type_text"],
    }

    async def extract_from_turn(self, user_msg: str, agent_response: str):
        """
        Спрашивает LLM: есть ли важная информация в этом диалоге?
        """
        extraction_prompt = f"""
Проанализируй диалог и извлеки ТОЛЬКО критичную информацию.

User: {user_msg}
Agent: {agent_response}

Верни JSON:
{{
  "dietary_restrictions": "аллергия на морепродукты",
  "people_count": 4,
  "budget": 2000,
  "location": "Красноярск"
}}

Если ничего критичного - верни {{}}.
"""

        response = self.llm.chat(extraction_prompt, temperature=0.2)
        extracted = json.loads(response)

        # Обновляем контекст
        for key, value in extracted.items():
            if value:
                self.extracted_context[key] = value

    def get_context_for_action(self, action_type: str) -> str:
        """
        Возвращает ТОЛЬКО релевантный контекст для данного действия
        """
        if not self.extracted_context:
            return ""

        relevant_items = []

        for context_key, context_value in self.extracted_context.items():
            # Проверяем релевантность
            if context_key in self.CONTEXT_RELEVANCE:
                relevant_actions = self.CONTEXT_RELEVANCE[context_key]

                if action_type in relevant_actions:
                    formatted = self._format_context_item(context_key, context_value)
                    relevant_items.append(formatted)

        if relevant_items:
            return "\n⚠️ ВАЖНАЯ ИНФОРМАЦИЯ:\n" + "\n".join(relevant_items)

        return ""
```

### 2. Интеграция в DialogueManager

```python
class DialogueManager:
    def __init__(self):
        self.agent = AIAgent()
        # Context Extraction Pattern
        self.context_extractor = ContextExtractor(self.agent.client)

    async def _dialogue_loop(self):
        # Получаем ответ агента
        response = self.agent.chat(user_input)

        # Автоматически извлекаем контекст
        await self.context_extractor.extract_from_turn(user_input, response)

    def _format_action_result(self, result: dict, action: dict) -> str:
        context = f"Действие: {action['action']}\n..."

        # Добавляем ТОЛЬКО релевантный контекст
        relevant_context = self.context_extractor.get_context_for_action(
            action['action']
        )
        if relevant_context:
            context += f"\n{relevant_context}"

        return context
```

## Примеры работы

### Пример 1: Автоматическое извлечение аллергий

```
👤 User: "Хочу заказать пиццу, но у меня аллергия на морепродукты"

🤖 Agent: "Понял, буду подбирать пиццу без морепродуктов"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 ContextExtractor автоматически извлек:
{
  "dietary_restrictions": "аллергия на морепродукты"
}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🤖 Agent выполняет: click_by_text("Мексиканская пицца")

📥 Контекст для действия click_by_text:
⚠️ ВАЖНАЯ ИНФОРМАЦИЯ:
🚨 ОГРАНИЧЕНИЯ: аллергия на морепродукты

✅ Агент видит ограничение и избегает морепродуктов!
```

### Пример 2: Контекстно-зависимая подача

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Извлеченный контекст:
{
  "dietary_restrictions": "без лактозы",
  "people_count": 4,
  "location": "Красноярск"
}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🤖 Действие: scroll()
📥 Контекст: (пустой)
   ↳ Для scroll ограничения не важны

🤖 Действие: click_by_text("Четыре сыра")
📥 Контекст:
   ⚠️ ВАЖНАЯ ИНФОРМАЦИЯ:
   🚨 ОГРАНИЧЕНИЯ: без лактозы
   👥 Количество человек: 4
   ↳ Для выбора блюда ограничения КРИТИЧНЫ

🤖 Действие: navigate("https://...")
📥 Контекст:
   ⚠️ ВАЖНАЯ ИНФОРМАЦИЯ:
   📍 Город: Красноярск
   ↳ Для навигации важен город
```

### Пример 3: Обновление контекста

```
👤 User: "Нас будет 2 человека"
🤖 Agent: "Хорошо, учту"

📊 Извлечено: {"people_count": 2}

━━━━━━━━━━━━━━━━━━━━━━━━

👤 User: "На самом деле нас будет 4"
🤖 Agent: "Обновил, теперь на 4 человек"

📊 Обновлено: {"people_count": 4}  # ← Автоматически!

━━━━━━━━━━━━━━━━━━━━━━━━

🤖 Действие: click_by_text(...)
📥 Контекст: 👥 Количество человек: 4  # ← Актуальное значение!
```

## Преимущества

### 1. Автономность ✅
```python
# Старый подход ❌
User: "Закажи пиццу"
Agent: "Есть ли у вас аллергии?"  # ← Навязчиво!

# Новый подход ✅
User: "Закажи пиццу, но я не ем морепродукты"
Agent: "Нашёл пиццу Маргарита - без морепродуктов"  # ← Умно!
```

### 2. Эффективность ✅
```python
# Старый подход ❌
def _format_action_result(...):
    context += self._format_user_restrictions()  # На КАЖДОМ действии
    # Даже на scroll, где это не нужно!

# Новый подход ✅
def _format_action_result(...):
    context += self.context_extractor.get_context_for_action(action_type)
    # Только там где релевантно
```

### 3. Расширяемость ✅
```python
# Добавить новый тип контекста очень легко:

CONTEXT_RELEVANCE = {
    "dietary_restrictions": ["click_by_text", ...],
    "people_count": ["click_by_text", ...],

    # Новый тип! Просто добавляем
    "delivery_time": ["type_text", "click_by_text"],
    "payment_method": ["click_by_text"],
}

# Форматтер тоже легко расширить
formatters = {
    ...
    "delivery_time": lambda v: f"⏰ Время доставки: {v}",
    "payment_method": lambda v: f"💳 Способ оплаты: {v}",
}
```

### 4. Чистая архитектура ✅
```
DialogueManager  ← Оркестрирует диалог
    ↓
ContextExtractor ← Отвечает за извлечение контекста
    ↓
LLM Client       ← Делает запросы к API
```

## Сравнение с альтернативами

### ❌ Альтернатива 1: Хардкод вопросов
```python
# Навязчиво и негибко
if "пицца" in user_input:
    response = "Есть ли у вас аллергии?"
    # Что если пользователь УЖЕ сказал?
```

### ❌ Альтернатива 2: Передача везде
```python
# Раздутый контекст на КАЖДОМ действии
context = f"""
Аллергии: {allergies}
Предпочтения: {preferences}
Бюджет: {budget}
...
"""
# Даже когда scroll делаем!
```

### ✅ Context Extraction Pattern
```python
# Автоматически, умно, эффективно
await extract_from_turn(user_msg, agent_response)
context = get_context_for_action(action_type)
# Только релевантное, только там где нужно
```

## Тестирование

```python
def test_get_context_for_action_dietary_restrictions():
    extractor = ContextExtractor(mock_client)
    extractor.extracted_context["dietary_restrictions"] = "аллергия на морепродукты"

    # Для click_by_text релевантно
    context = extractor.get_context_for_action("click_by_text")
    assert "🚨 ОГРАНИЧЕНИЯ" in context
    assert "аллергия на морепродукты" in context

    # Для scroll НЕ релевантно
    context = extractor.get_context_for_action("scroll")
    assert context == ""
```

## Заключение

Context Extraction Pattern решает проблему хранения и передачи пользовательского контекста:

1. **Автоматическое извлечение** - LLM сам определяет что важно
2. **Контекстно-зависимая подача** - передается только там где нужно
3. **Чистая архитектура** - отдельный класс с четкой ответственностью
4. **Легко расширяется** - новые типы контекста добавляются тривиально

Это пример хорошей архитектуры в AI-агентах! 🎯
