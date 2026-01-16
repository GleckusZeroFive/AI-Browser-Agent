# Changelog: Управление токенами и контекстом

## Проблема

При использовании fallback-моделей возникала ошибка **413 Payload Too Large**, когда система переключалась с модели с большим лимитом токенов на модель с меньшим лимитом, не учитывая размер текущего контекста разговора.

### Пример ошибки:
```
Error code: 413 - {'error': {'message': 'Request too large for model
`meta-llama/llama-4-maverick-17b-128e-instruct` in organization ...
on tokens per minute (TPM): Limit 6000, Requested 8056, ...
```

## Решение

Реализована система умного управления контекстом разговора с автоматическим подсчетом токенов и выбором подходящих моделей.

## Изменения

### 1. Конфигурация ([src/config.py](src/config.py:41-55))

Добавлены новые настройки:

```python
# Лимиты токенов для каждой модели (tokens per minute)
MODEL_TOKEN_LIMITS = {
    "meta-llama/llama-4-scout-17b-16e-instruct": 14400,
    "meta-llama/llama-4-maverick-17b-128e-instruct": 6000,
    "llama-3.3-70b-versatile": 6000,
    "llama-3.1-8b-instant": 30000,
}

# Управление контекстом разговора
MAX_CONTEXT_MESSAGES: int = 20  # Максимальное количество сообщений
CONTEXT_TRIM_TO: int = 12  # До скольких сокращать при превышении
SAFE_TOKEN_MARGIN: float = 0.7  # Использовать 70% от лимита для безопасности
```

### 2. AIAgent ([src/agent/ai_agent.py](src/agent/ai_agent.py))

#### Новые методы:

**`_estimate_tokens(text: str) -> int`**
- Приблизительная оценка количества токенов в тексте
- Учитывает разницу между кириллицей (~2.5 символа/токен) и латиницей (~4 символа/токен)

**`_calculate_context_tokens() -> int`**
- Подсчет общего количества токенов во всей истории разговора

**`_trim_conversation_history(max_tokens: int)`**
- Сокращение истории разговора при превышении лимита
- Сохраняет системный промпт и последние N сообщений
- Логирует информацию о сокращении

**`_get_suitable_fallback_model(current_tokens: int, exclude_model: str) -> Optional[str]`**
- Выбор подходящей fallback-модели с учетом размера контекста
- Возвращает модель с наибольшим лимитом, который подходит для текущего контекста
- Учитывает безопасный запас (70% от лимита)

#### Улучшенный метод `chat()`:

1. **Проактивная проверка размера контекста**:
   ```python
   current_tokens = self._calculate_context_tokens()
   self.logger.info(f"Размер контекста: {current_tokens} токенов, {len(self.conversation_history)} сообщений")
   ```

2. **Умный выбор модели до отправки запроса**:
   ```python
   if current_tokens > safe_limit:
       # Пробуем найти модель с большим лимитом
       alternative_model = self._get_suitable_fallback_model(current_tokens)
       if alternative_model:
           model_to_use = alternative_model
       else:
           # Сокращаем контекст
           self._trim_conversation_history(safe_limit)
   ```

3. **Обработка ошибки 413**:
   ```python
   if "413" in error_str or "payload too large" in error_str.lower():
       # Сокращаем контекст
       self._trim_conversation_history(safe_limit)
       # Ищем модель с большим лимитом
       alternative_model = self._get_suitable_fallback_model(current_tokens)
       continue
   ```

## Преимущества

✅ **Предотвращение ошибки 413**: Система проверяет размер контекста до отправки запроса

✅ **Автоматическое сокращение**: При превышении лимита история автоматически сокращается

✅ **Умный выбор моделей**: Система выбирает модели с учетом текущего размера контекста

✅ **Прозрачность**: Все действия логируются и отображаются пользователю

✅ **Сохранение контекста**: Системный промпт и последние сообщения всегда сохраняются

## Тестирование

Создан тестовый файл [test_token_management.py](test_token_management.py) для проверки:
- Оценки токенов
- Подсчета контекста
- Выбора модели
- Сокращения истории

Запуск тестов:
```bash
source venv/bin/activate
python test_token_management.py
```

## Результат

Теперь система:
1. **НЕ допускает** отправку запросов, превышающих лимит модели
2. **Автоматически выбирает** подходящую модель для текущего контекста
3. **Сокращает историю** когда это необходимо
4. **Информирует пользователя** о всех операциях

Ошибка 413 теперь обрабатывается корректно и не приводит к сбоям в работе агента.
