# Тестирование AI Browser Agent

Руководство по запуску и написанию тестов для проекта.

## Установка зависимостей для тестирования

```bash
# Установить зависимости для разработки
pip install -r requirements-dev.txt
```

## Запуск тестов

### Запустить все тесты

```bash
pytest
```

### Запустить конкретные типы тестов

```bash
# Только unit тесты (быстрые)
pytest -m unit

# Только integration тесты
pytest -m integration

# Без медленных тестов
pytest -m "not slow"

# Только тесты с браузером
pytest -m browser
```

### Запустить тесты из конкретного файла

```bash
pytest tests/test_model_fallback.py
```

### Запустить конкретный тест

```bash
pytest tests/test_model_fallback.py::test_specific_function
```

### Запуск с дополнительными опциями

```bash
# Остановиться на первой ошибке
pytest -x

# Запустить последние упавшие тесты
pytest --lf

# Показать print() в тестах
pytest -s

# Параллельный запуск (требует pytest-xdist)
pytest -n auto

# Без покрытия кода (быстрее)
pytest --no-cov
```

## Покрытие кода

После запуска тестов с покрытием (по умолчанию включено в pytest.ini):

```bash
# Открыть HTML отчет о покрытии
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## Структура тестов

```
tests/
├── conftest.py              # Общие фикстуры
├── unit/                    # Unit тесты (изолированные)
│   ├── test_config.py
│   ├── test_system_check.py
│   └── test_version_info.py
├── integration/             # Integration тесты (с внешними сервисами)
│   ├── test_action_limit.py
│   └── test_models_comparison.py
└── test_model_fallback.py   # Тесты fallback моделей
```

## Написание тестов

### Пример unit теста

```python
import pytest
from src.config import Config

def test_config_api_key(mock_config):
    """Тест получения API ключа"""
    api_key = Config.get_api_key()
    assert api_key == "test_api_key_123"

def test_config_missing_api_key(monkeypatch):
    """Тест ошибки при отсутствии API ключа"""
    monkeypatch.setattr(Config, "GROQ_API_KEY", "")

    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        Config.get_api_key()
```

### Пример async теста

```python
import pytest

@pytest.mark.asyncio
async def test_browser_start(mock_browser_tools):
    """Тест запуска браузера"""
    result = await mock_browser_tools.start_browser()

    assert result["status"] == "success"
    mock_browser_tools.start_browser.assert_called_once()
```

### Пример интеграционного теста с браузером

```python
import pytest

@pytest.mark.browser
@pytest.mark.slow
@pytest.mark.asyncio
async def test_real_browser_navigation(real_browser_tools):
    """Интеграционный тест навигации в реальном браузере"""
    result = await real_browser_tools.navigate("https://example.com")

    assert result["status"] == "success"
    assert "example.com" in result["url"]
```

### Использование маркеров

```python
@pytest.mark.unit
def test_fast_unit():
    """Быстрый unit тест"""
    pass

@pytest.mark.integration
@pytest.mark.api
def test_with_api(skip_if_no_api_key):
    """Тест требующий API ключ"""
    pass

@pytest.mark.slow
@pytest.mark.browser
async def test_browser_interaction():
    """Медленный тест с браузером"""
    pass
```

## Фикстуры

Доступные фикстуры определены в `conftest.py`:

- `mock_config` - мок конфигурации
- `mock_browser_tools` - мок браузерных инструментов
- `mock_ai_agent` - мок AI агента
- `real_browser_tools` - реальный браузер (для интеграционных тестов)
- `temp_env_file` - временный .env файл
- `sample_page_html` - пример HTML страницы
- `sample_action` - пример действия
- `skip_if_no_api_key` - пропуск теста без API ключа

## Отладка тестов

### Использование debugger

```python
def test_with_debugger():
    import ipdb; ipdb.set_trace()  # Точка останова
    # ваш код
```

### Запуск с отладкой

```bash
# Остановиться на первой ошибке и открыть debugger
pytest --pdb

# Открыть debugger при исключении
pytest --pdb --pdbcls=IPython.terminal.debugger:TerminalPdb
```

## CI/CD

Для использования в CI/CD (GitHub Actions, GitLab CI):

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install -r requirements-dev.txt
          playwright install firefox
      - name: Run tests
        run: pytest -m "not browser" --cov
```

## Лучшие практики

1. **Изолируйте тесты** - каждый тест должен быть независимым
2. **Используйте моки** - для внешних зависимостей (API, браузер)
3. **Называйте тесты понятно** - `test_function_name_when_condition_should_result`
4. **Группируйте тесты** - используйте маркеры и структуру папок
5. **Тестируйте edge cases** - граничные случаи и ошибки
6. **Быстрые unit тесты** - основная масса тестов должна быть быстрой
7. **Минимум интеграционных тестов** - они медленные, используйте разумно

## Troubleshooting

### Тесты не находятся

Убедитесь что:
- Файлы начинаются с `test_`
- Функции начинаются с `test_`
- Установлен pytest: `pip install pytest`

### Ошибки импорта

```bash
# Установите проект в editable mode
pip install -e .
```

### Тесты с браузером падают

```bash
# Переустановите браузеры
playwright install firefox

# Запустите только без браузерных тестов
pytest -m "not browser"
```

## Полезные ссылки

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Playwright Python](https://playwright.dev/python/docs/intro)
