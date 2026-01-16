# Vision API Integration

## Описание

Агент теперь использует **Groq Vision API** (модели Llama 3.2 Vision) для анализа скриншотов страниц вместо передачи большого объема текста. Это значительно улучшает:

- ⚡ **Скорость работы** - меньше токенов = быстрее обработка
- 💰 **Экономию токенов** - вместо 3000 символов текста (~1200 токенов) отправляется только изображение
- 🎯 **Точность** - модель видит визуальную структуру страницы
- 🚀 **Эффективность** - меньше нагрузки на rate limits

## Что изменилось

### 1. Конфигурация ([src/config.py](src/config.py))

Добавлены новые настройки:

```python
# Режим Vision (по умолчанию включен)
USE_VISION: bool = os.getenv("USE_VISION", "true").lower() == "true"

# Модель для Vision-запросов
VISION_MODEL: str = "llama-3.2-90b-vision-preview"

# Лимиты токенов для Vision-моделей
MODEL_TOKEN_LIMITS = {
    "llama-3.2-90b-vision-preview": 6000,
    "llama-3.2-11b-vision-preview": 14400,
}
```

### 2. AI Agent ([src/agent/ai_agent.py](src/agent/ai_agent.py))

Добавлен новый метод `chat_with_vision()`:

- Кодирует скриншот в base64
- Отправляет изображение вместе с текстовым запросом
- Автоматически fallback на текстовый режим при ошибке

### 3. Dialogue Manager ([src/dialogue_manager.py](src/dialogue_manager.py))

Умная логика выбора режима:

- **Vision используется** для: navigate, click_by_text, scroll_down, scroll_up, search_and_type
- **Текст используется** для: ошибок, простых действий (press_key, wait)
- Дополнительное ожидание загрузки перед скриншотом (2 сек для navigate/search)

### 4. Browser Tools ([src/tools/browser_tools.py](src/tools/browser_tools.py))

Улучшено ожидание загрузки:

- `navigate()`: используется `networkidle` + 1.5 сек ожидания
- `click_by_text()`: 1.5 сек после клика
- `scroll_down()`: 1.0 сек для lazy-loading контента

### 5. Промпты ([src/prompts/prompt_manager.py](src/prompts/prompt_manager.py))

Обновлены инструкции для агента:

- Удалены упоминания `get_page_text()`
- Добавлено: "После каждого действия получаешь СКРИНШОТ"
- Инструкции теперь ориентированы на визуальный анализ

## Использование

### Включить/выключить Vision

В файле `.env`:

```bash
# Включить Vision (по умолчанию)
USE_VISION=true

# Выключить Vision (вернуться к текстовому режиму)
USE_VISION=false
```

### Выбор модели

Для экономии токенов можно использовать меньшую модель:

```python
# В src/config.py
VISION_MODEL: str = "llama-3.2-11b-vision-preview"  # Вместо 90b
```

**Сравнение моделей:**

| Модель | Размер | TPM Limit | Качество | Рекомендация |
|--------|--------|-----------|----------|--------------|
| llama-3.2-90b-vision-preview | 90B | 6,000 | Высокое | Для сложных задач |
| llama-3.2-11b-vision-preview | 11B | 14,400 | Хорошее | Для большинства задач |

## Технические детали

### Формат запроса к Vision API

```python
{
    "role": "user",
    "content": [
        {"type": "text", "text": "Что на этой странице?"},
        {
            "type": "image_url",
            "image_url": {
                "url": "data:image/png;base64,iVBORw0KGgo..."
            }
        }
    ]
}
```

### Логика принятия решений

```python
def _should_use_vision(action, result):
    # Vision полезен для:
    vision_actions = [
        "navigate",       # Увидеть что на странице
        "click_by_text",  # Проверить результат клика
        "scroll_down",    # Увидеть новый контент
        "scroll_up",      # Увидеть контент выше
        "search_and_type",# Увидеть результаты поиска
        "close_modal",    # Проверить что окно закрылось
    ]
    return action in vision_actions and result["status"] == "success"
```

### Ожидание загрузки контента

Критично для динамических сайтов (React, Vue, SPA):

1. **Навигация**: `networkidle` + 1.5s + дополнительно 2s перед скриншотом
2. **Клик**: 1.5s после клика
3. **Скролл**: 1.0s для lazy-loading
4. **Поиск**: 2s после ввода + результаты

## Преимущества

### До (текстовый режим)
```
Запрос: get_page_text() → 3000 символов → ~1200 токенов
Проблемы:
- Медленная обработка
- Быстрое исчерпание rate limits
- Нет визуального контекста
- Потеря информации о структуре
```

### После (Vision режим)
```
Запрос: screenshot → изображение → ~200-300 токенов эквивалента
Преимущества:
- Быстрая обработка
- Экономия токенов (в 4-5 раз)
- Визуальный контекст
- Видит структуру, цвета, расположение
```

## Troubleshooting

### Vision модель недоступна

Если Vision-модель недоступна, агент автоматически переключится на текстовый режим:

```
⚠️  Vision-модель недоступна, переключаюсь на текстовую модель
```

### Скриншот не создается

Проверьте:
1. Браузер запущен и работает
2. Папка `screenshots/` существует и доступна для записи
3. Достаточно места на диске

### Медленная работа

Если Vision-запросы слишком долгие:
1. Попробуйте меньшую модель (`llama-3.2-11b-vision-preview`)
2. Проверьте интернет-соединение
3. Уменьшите `SCREENSHOT_MAX_SIZE` в config.py

## Совместимость

- ✅ Groq API (Llama 3.2 Vision)
- ✅ Python 3.8+
- ✅ Playwright (для скриншотов)
- ✅ OpenAI SDK (для совместимости с API)

## Источники

- [Groq Console Documentation](https://console.groq.com/docs)
- [Vision OCR Example](https://github.com/0xSaurabhx/vision-ocr)
- [Llama 3.2 Vision Models](https://groq.com/inference/)
