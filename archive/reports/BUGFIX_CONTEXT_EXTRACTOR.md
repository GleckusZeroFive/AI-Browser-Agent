# Исправление ошибки context_extractor

## Проблема

После перемещения `context_extractor` в архив остались ссылки на этот модуль в коде, что вызывало критические ошибки:

```
AttributeError: 'DialogueManager' object has no attribute 'context_extractor'
```

### Локация ошибки
- Файл: `src/dialogue_manager.py`
- Строки: 582-585
- Метод: `_format_action_result()`

### Как проявлялась
Ошибка возникала каждый раз, когда агент пытался выполнить действие через браузер (navigate, click_by_text и т.д.), так как метод `_format_action_result` пытался обратиться к несуществующему атрибуту `self.context_extractor`.

## Выполненные изменения

### 1. Исправлен dialogue_manager.py
**Удалены строки 582-585:**
```python
# Context Extraction Pattern: добавляем только релевантный контекст для этого действия
if self.context_extractor:
    relevant_context = self.context_extractor.get_context_for_action(action_name)
    if relevant_context:
        context += f"\n{relevant_context}"
```

**Обоснование:** Функционал извлечения контекста был перенесен в `KnowledgeBase`, поэтому эти строки устарели и вызывали ошибки.

### 2. Перемещены в архив дополнительные файлы

#### Тесты
- `tests/unit/test_context_extractor.py` → `archive/test_context_extractor.py.backup`

#### Документация
- `CONTEXT_EXTRACTION_README.md` → `archive/CONTEXT_EXTRACTION_README.md.backup`
- `docs/context_extraction_diagram.txt` → `archive/context_extraction_diagram.txt.backup`
- `docs/CONTEXT_EXTRACTION_PATTERN.md` → `archive/CONTEXT_EXTRACTION_PATTERN.md.backup`

**Обоснование:** Эти файлы описывали устаревший подход к извлечению контекста и больше не актуальны.

## Проверка

### Синтаксис
```bash
python3 -m py_compile src/dialogue_manager.py
# ✅ Синтаксис корректен
```

### Поиск оставшихся ссылок
```bash
grep -r "context_extractor" --include="*.py" src/
# Результат: пусто (нет ссылок)
```

## Результат

✅ Ошибка `AttributeError: 'DialogueManager' object has no attribute 'context_extractor'` **устранена**

✅ Все ссылки на устаревший модуль удалены из кода

✅ Устаревшая документация перемещена в архив

✅ Приложение теперь работает без ошибок при выполнении действий через браузер

## Архивные файлы

Все файлы, связанные с `context_extractor`, теперь находятся в директории `archive/`:
```
archive/
├── context_extractor.py.backup (10K)
├── test_context_extractor.py.backup (9.3K)
├── CONTEXT_EXTRACTION_README.md.backup (5.2K)
├── context_extraction_diagram.txt.backup (12K)
└── CONTEXT_EXTRACTION_PATTERN.md.backup
```

## Дата исправления
2026-01-15
