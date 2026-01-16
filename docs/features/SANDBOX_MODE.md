# Sandbox Mode - Режим самотестирования агента

## Концепция

Sandbox Mode - это режим, в котором агент **сам себе пользователь**. Вместо того чтобы ждать, пока пользователь наткнётся на баг, агент проактивно исследует свой функционал и фиксирует проблемы.

## Зачем это нужно?

### Проблема
После каждого нового бага приходится вручную:
1. Воспроизводить ошибку
2. Чинить конкретную функцию
3. Надеяться что больше ничего не сломалось

Это бесконечный цикл 🔄

### Решение
Агент в sandbox mode:
- ✅ Тестирует все свои инструменты автоматически
- ✅ Не падает с ошибками, а фиксирует их
- ✅ Пробует альтернативные подходы
- ✅ Создаёт подробный отчёт о функциональности
- ✅ Накапливает статистику ошибок

## Как использовать

### Запуск sandbox mode

```bash
python main.py --sandbox
```

### Что происходит

1. **Инициализация**
   - Запускается браузер
   - Загружается список всех доступных действий
   - Генерируются тестовые сценарии

2. **Тестирование**
   - Агент последовательно проверяет каждое действие
   - Фиксирует успехи и ошибки
   - Не падает, а продолжает тестирование

3. **Отчёт**
   - Создаётся детальный JSON отчёт
   - Выводится краткая сводка в консоль
   - Сохраняется в `data/sandbox_reports/`

## Структура отчёта

```json
{
  "timestamp": "2026-01-15T20:30:00",
  "summary": {
    "total_tests": 15,
    "successful": 12,
    "failed": 2,
    "skipped": 1,
    "success_rate": 80.0
  },
  "functionality_map": {
    "navigate": "working",
    "get_page_text": "working",
    "click_by_text": "broken",
    "scroll_down": "working"
  },
  "errors": {
    "by_type": {
      "TypeError": 1,
      "AttributeError": 1
    },
    "by_action": {
      "click_by_text": [
        {
          "scenario": "Клик по тексту 'Example'",
          "error": "Element not found",
          "error_type": "TypeError"
        }
      ]
    }
  },
  "executor_stats": {
    "total_errors": 2,
    "by_type": {"TypeError": 1, "AttributeError": 1},
    "by_action": {"click_by_text": 2}
  },
  "detailed_results": [...]
}
```

## Ключевые возможности

### 1. Graceful Degradation

Вместо падения агент:
```python
try:
    result = execute_action(action)
except TypeError as e:
    # Фиксирует ошибку
    log_error(action, e)
    # Возвращает structured error
    return {
        "status": "error",
        "error_type": "parameter_error",
        "message": "...",
        "suggestion": "Проверьте формат параметров"
    }
```

### 2. Автогенерация тестовых сценариев

Для каждого действия создаются реалистичные тесты:
- `navigate` → Переход на Google, Example.com
- `get_page_text` → Получение текста после навигации
- `click_by_text` → Клик по реальному элементу на странице
- `scroll_down/up` → Прокрутка с разными параметрами

### 3. Интеграция с ActionExecutor

Sandbox использует встроенный error tracking:
```python
executor.get_error_summary()
# {
#   "total_errors": 5,
#   "by_type": {"TypeError": 3, "AttributeError": 2},
#   "by_action": {"click_by_text": 5},
#   "recent_errors": [...]
# }
```

### 4. Увеличенные лимиты

В sandbox mode агент получает:
- 🔼 4000 токенов вместо 2000
- ⏰ Больше времени на рассуждения
- 📝 Возможность детально логировать процесс

## Примеры использования

### Базовое тестирование

```bash
python main.py --sandbox
```

Результат:
```
🧪 SANDBOX MODE - САМОТЕСТИРОВАНИЕ АГЕНТА
======================================================================

📋 Доступно действий: 13
   navigate, click_by_text, get_page_text, scroll_down, ...

📝 Сгенерировано тестовых сценариев: 15

======================================================================
ТЕСТ 1/15: Навигация на Google
======================================================================
   📍 Навигация на https://www.google.com...
   🔧 Выполнение: navigate
      Параметры: {'url': 'https://www.google.com'}
   ✅ Успех

...

📊 ИТОГОВАЯ СВОДКА
======================================================================

✅ Успешных тестов: 12/15 (80.0%)
❌ Неудачных тестов: 2/15
⏭️  Пропущенных тестов: 1/15

📋 СТАТУС ФУНКЦИЙ:
   ✅ navigate: working
   ✅ get_page_text: working
   ❌ click_by_text: broken
   ✅ scroll_down: working
```

### Анализ отчёта

```bash
# Посмотреть последний отчёт
cat data/sandbox_reports/sandbox_report_20260115_203000.json | jq .summary

# Найти все проблемные действия
cat data/sandbox_reports/sandbox_report_*.json | jq '.errors.by_action'

# Статистика по типам ошибок
cat data/sandbox_reports/sandbox_report_*.json | jq '.errors.by_type'
```

## Интеграция в workflow

### 1. Перед деплоем

```bash
# Запускаем sandbox test
python main.py --sandbox

# Проверяем success_rate
if [ $(jq '.summary.success_rate' data/sandbox_reports/latest.json) -lt 90 ]; then
    echo "Качество ниже 90%, деплой отменён"
    exit 1
fi
```

### 2. После исправления бага

```bash
# Запускаем sandbox
python main.py --sandbox

# Сравниваем с предыдущим отчётом
diff data/sandbox_reports/before.json data/sandbox_reports/after.json
```

### 3. Регулярный мониторинг

```bash
# Cron job каждый день
0 3 * * * cd /path/to/agent && python main.py --sandbox
```

## Архитектура

```
┌──────────────────┐
│   Main.py        │
│   --sandbox      │
└────────┬─────────┘
         │
         v
┌──────────────────────────────────┐
│   DialogueManager                │
│   start(sandbox_mode=True)       │
└────────┬─────────────────────────┘
         │
         v
┌────────────────────────────────────────┐
│   SandboxMode                          │
│   - generate_test_scenarios()          │
│   - run_test_scenario()                │
│   - generate_report()                  │
└────────┬───────────────────────────────┘
         │
         v
┌──────────────────────────────────────┐
│   ActionExecutor (with error tracking)│
│   - execute()                         │
│   - _log_error()                      │
│   - get_error_summary()               │
└───────────────────────────────────────┘
```

## Roadmap

### Планируемые улучшения

1. **AI-генерация сценариев**
   - Агент сам придумывает тесты на основе доступных действий
   - Использует LLM для креативных сценариев

2. **Адаптивное тестирование**
   - Фокус на проблемных функциях
   - Повторное тестирование с разными параметрами

3. **Сравнение отчётов**
   - Автоматическое сравнение с предыдущими запусками
   - Детекция регрессий

4. **Интеграция с CI/CD**
   - GitHub Actions workflow
   - Автоматические отчёты в PR

## FAQ

**Q: Сколько времени занимает sandbox test?**
A: ~2-5 минут в зависимости от количества действий

**Q: Можно ли запустить sandbox в headless mode?**
A: Да, установите `BROWSER_HEADLESS=true` в `.env`

**Q: Что делать если success_rate низкий?**
A:
1. Изучите отчёт в `data/sandbox_reports/`
2. Найдите повторяющиеся ошибки
3. Исправьте проблемные действия
4. Запустите sandbox снова

**Q: Нужен ли API ключ для sandbox?**
A: Да, sandbox использует AI агента для генерации сценариев

## Заключение

Sandbox Mode превращает процесс отладки из реактивного в проактивный. Вместо бесконечных багфиксов вы получаете:

- 📊 Статистику здоровья системы
- 🔍 Автоматическое обнаружение проблем
- 📝 Детальные отчёты для анализа
- 🎯 Фокус на качестве перед деплоем

**Используйте sandbox mode регулярно** - это сэкономит часы отладки! 🚀
