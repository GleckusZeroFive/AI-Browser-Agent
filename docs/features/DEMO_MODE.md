# Demo Mode - Руководство разработчика

Это руководство для разработчиков, которые хочет интегрировать Demo Mode в свои функции агента.

## Содержание

- [Быстрый старт](#быстрый-старт)
- [Декораторы](#декораторы)
- [Визуальные маркеры](#визуальные-маркеры)
- [Логирование](#логирование)
- [Конфигурация](#конфигурация)
- [Примеры](#примеры)

## Быстрый старт

### 1. Добавление логирования к функции

```python
from src.utils.logging_decorator import log_execution

@log_execution
def my_action(param1, param2):
    """Моя функция агента"""
    # Ваш код
    return result
```

### 2. Добавление Demo Mode к функции

```python
from src.utils.demo_mode import demo_action

@demo_action
def my_action(param1, param2):
    """Моя функция агента с поддержкой demo mode"""
    # Ваш код
    return result
```

Декоратор `@demo_action` автоматически включает:
- Логирование выполнения
- Показ кода перед выполнением
- Задержки до и после действия
- Отображение информации о параметрах

### 3. Для асинхронных функций

```python
from src.utils.demo_mode import demo_async_action

@demo_async_action
async def my_async_action(param1, param2):
    """Моя асинхронная функция"""
    # Ваш код
    return result
```

## Декораторы

### `@log_execution`

Базовый декоратор логирования. Логирует:
- Имя функции и файл:строка
- Переданные аргументы
- Время начала и окончания
- Время выполнения
- Результат или ошибку

**Использование:**

```python
from src.utils.logging_decorator import log_execution

@log_execution
def process_data(data):
    return data.upper()

result = process_data("hello")
# Лог: ⏯️  START | module.py:10 | process_data('hello')
# Лог: ✅ SUCCESS | module.py:10 | process_data | Duration: 0.001s | Result: 'HELLO'
```

### `@log_async_execution`

Для асинхронных функций:

```python
from src.utils.logging_decorator import log_async_execution

@log_async_execution
async def fetch_data(url):
    # async code
    return data
```

### `@demo_action`

Полнофункциональный декоратор для demo mode. Включает логирование + визуализацию.

**Когда использовать:**
- Для действий агента, которые нужно демонстрировать
- Когда нужны задержки между действиями
- Когда важно показать выполняемый код

**Что делает:**
1. Показывает панель с информацией о действии
2. Отображает код функции с подсветкой
3. Делает задержку `before_action`
4. Выполняет функцию
5. Показывает результат и время выполнения
6. Делает задержку `after_action`

### `@demo_async_action`

Асинхронная версия `@demo_action`.

## Визуальные маркеры

Визуальные маркеры добавляют анимацию и подсветку в браузер.

### Инициализация

```python
from src.utils.visual_markers import VisualMarkers

# В функции, где есть доступ к Playwright Page
markers = VisualMarkers(page, enabled=True)
```

### Методы

#### `highlight_click(selector, duration=600)`

Подсвечивает элемент при клике.

```python
await markers.highlight_click("button.submit", duration=800)
await page.click("button.submit")
```

#### `highlight_click_by_text(text, duration=600)`

Подсвечивает элемент по тексту.

```python
await markers.highlight_click_by_text("Войти", duration=600)
await page.click("text=Войти")
```

#### `show_typing(selector, duration=1000)`

Показывает индикатор ввода текста.

```python
await markers.show_typing("input[name='email']", duration=1500)
await page.fill("input[name='email']", "user@example.com")
```

#### `show_scroll_indicator(direction='down', duration=1000)`

Показывает индикатор скролла.

```python
await markers.show_scroll_indicator("down", duration=800)
await page.mouse.wheel(0, 500)
```

#### `show_action_indicator(action, duration=2000)`

Показывает баннер с описанием действия.

```python
await markers.show_action_indicator("Поиск товара...", duration=2000)
# выполнение поиска
```

#### `show_spinner(show=True)`

Показывает/скрывает спиннер ожидания.

```python
await markers.show_spinner(True)
await page.wait_for_load_state("networkidle")
await markers.show_spinner(False)
```

#### `cleanup()`

Очищает все визуальные маркеры.

```python
await markers.cleanup()
```

### Пример интеграции в action_executor

```python
from src.utils.visual_markers import get_visual_markers
from src.utils.demo_mode import get_demo_mode

async def execute_click(page, selector):
    """Выполнить клик с визуальными маркерами"""
    demo = get_demo_mode()
    markers = get_visual_markers(page, enabled=demo.config.visual_markers_enabled)

    if demo.enabled:
        # Показываем что будем кликать
        await markers.show_action_indicator(f"Клик по {selector}")
        await markers.highlight_click(selector)

    # Выполняем клик
    await page.click(selector)

    if demo.enabled:
        # Задержка после действия
        await demo.delay("after_action")
```

## Логирование

### Структура лог-файла

Логи сохраняются в `logs/execution_YYYYMMDD.log`:

```
2024-01-15 12:30:45 | INFO     | action_executor.py:123 | execute_action | ⏯️  START | click_by_text("Маргарита")
2024-01-15 12:30:46 | INFO     | action_executor.py:123 | execute_action | ✅ SUCCESS | Duration: 0.342s
```

### Уровни логирования

- `⏯️  START` - начало выполнения функции
- `✅ SUCCESS` - успешное завершение
- `❌ ERROR` - ошибка выполнения

### Просмотр логов

```bash
# Запуск log viewer
python log_viewer.py

# Просмотр конкретного файла
python log_viewer.py logs/execution_20240115.log
```

## Конфигурация

### Файл demo_config.yaml

```yaml
demo_mode:
  enabled: false  # Включить demo mode постоянно

  delays:
    before_action: 1.0    # Задержка перед действием (сек)
    after_action: 0.5     # Задержка после действия (сек)
    visual_indicator: 1.5 # Длительность индикаторов (сек)
    code_to_action: 0.8   # Задержка между кодом и действием (сек)

  visual_markers:
    enabled: true           # Включить маркеры
    highlight_clicks: true  # Подсветка кликов
    show_typing: true       # Анимация ввода
    show_scroll: true       # Индикатор скролла
    show_action_indicator: true  # Баннер действия
    animation_duration: 600      # Длительность анимаций (мс)

  logging:
    level: verbose          # minimal, normal, verbose
    show_code_line: true    # Показывать код
    show_function_name: true  # Показывать имя функции
    show_arguments: true    # Показывать аргументы
    show_duration: true     # Показывать время
    colorized_console: true # Цветной вывод
    detailed_log_file: "logs/demo_execution.log"
```

### Программное изменение конфигурации

```python
from src.utils.demo_mode import DemoModeConfig, get_demo_mode

# Загрузить конфигурацию
config = DemoModeConfig("demo_config.yaml")

# Изменить настройки
config.config["demo_mode"]["delays"]["before_action"] = 2.0

# Создать demo mode с новой конфигурацией
demo = get_demo_mode(config)
```

## Примеры

### Пример 1: Простая функция с логированием

```python
from src.utils.logging_decorator import log_execution

@log_execution
def search_product(name, category):
    """Поиск товара"""
    results = database.query(name, category)
    return results

# Использование
products = search_product("pizza", "food")
```

**Вывод в лог:**
```
2024-01-15 12:30:00 | INFO | search.py:10 | search_product | ⏯️  START | search_product('pizza', 'food')
2024-01-15 12:30:01 | INFO | search.py:10 | search_product | ✅ SUCCESS | Duration: 0.823s | Result: [<Product>, ...]
```

### Пример 2: Функция с demo mode

```python
from src.utils.demo_mode import demo_action

@demo_action
def add_to_cart(product_id, quantity):
    """Добавить товар в корзину"""
    cart.add(product_id, quantity)
    return {"status": "success"}

# Использование
result = add_to_cart(123, 2)
```

**При включенном demo mode:**
1. Показывается панель: "Действие #1" с функцией и аргументами
2. Отображается код функции с подсветкой
3. Задержка 1.0 сек (before_action)
4. Выполнение функции
5. Показ результата и времени
6. Задержка 0.5 сек (after_action)

### Пример 3: Асинхронная функция с визуальными маркерами

```python
from src.utils.demo_mode import demo_async_action
from src.utils.visual_markers import get_visual_markers

@demo_async_action
async def click_button(page, text):
    """Кликнуть по кнопке с текстом"""
    from src.utils.demo_mode import get_demo_mode

    demo = get_demo_mode()
    markers = get_visual_markers(page, enabled=demo.config.visual_markers_enabled)

    if demo.enabled:
        await markers.show_action_indicator(f"Клик по кнопке '{text}'")
        await markers.highlight_click_by_text(text)

    await page.click(f"text={text}")

# Использование
await click_button(page, "Купить")
```

### Пример 4: Комплексное действие

```python
from src.utils.demo_mode import demo_async_action, get_demo_mode
from src.utils.visual_markers import get_visual_markers

@demo_async_action
async def fill_form(page, data):
    """Заполнить форму"""
    demo = get_demo_mode()
    markers = get_visual_markers(page, enabled=demo.enabled)

    for field, value in data.items():
        if demo.enabled:
            await markers.show_action_indicator(f"Заполнение поля {field}")
            await markers.show_typing(f"input[name='{field}']", duration=1500)

        await page.fill(f"input[name='{field}']", value)

        if demo.enabled:
            await demo.delay("after_action")

    # Клик по кнопке отправки
    if demo.enabled:
        await markers.highlight_click("button[type='submit']")

    await page.click("button[type='submit']")

# Использование
await fill_form(page, {
    "email": "user@example.com",
    "name": "John Doe",
    "phone": "+1234567890"
})
```

## Best Practices

1. **Используйте `@demo_action` для всех публичных действий агента**
   - Это обеспечивает консистентное логирование
   - Автоматически поддерживает demo mode

2. **Добавляйте визуальные маркеры только когда `demo.enabled`**
   - Проверяйте `get_demo_mode().enabled` перед использованием маркеров
   - Это избегает overhead в production

3. **Давайте осмысленные описания в `show_action_indicator`**
   - Используйте глаголы: "Поиск товара...", "Клик по кнопке..."
   - Будьте конкретны: не "Действие", а "Добавление в корзину"

4. **Настраивайте задержки под свои нужды**
   - Для коротких действий: 0.5-1.0 сек
   - Для сложных действий: 1.5-2.0 сек
   - Для критически важных моментов: 2.0+ сек

5. **Очищайте маркеры после завершения**
   - Вызывайте `markers.cleanup()` в конце сценария
   - Или используйте context manager (будущее улучшение)

## Отладка

### Проверка включен ли demo mode

```python
from src.utils.demo_mode import get_demo_mode

demo = get_demo_mode()
print(f"Demo mode enabled: {demo.enabled}")
print(f"Delays: {demo.config.delays}")
print(f"Visual markers: {demo.config.visual_markers_enabled}")
```

### Принудительное включение

```python
from src.utils.demo_mode import initialize_demo_mode

# Включить независимо от конфига
initialize_demo_mode(enabled=True)
```

### Просмотр логов в реальном времени

```bash
# Терминал 1: Запуск агента
python main.py --demo-mode

# Терминал 2: Просмотр логов
python log_viewer.py
```

## FAQ

**Q: Как отключить demo mode если он включен в конфиге?**

A: Запускайте без флага `--demo-mode`, тогда используется стандартная конфигурация.

**Q: Можно ли использовать только логирование без demo mode?**

A: Да, используйте `@log_execution` вместо `@demo_action`.

**Q: Визуальные маркеры не показываются, что делать?**

A: Проверьте:
1. `demo_mode.enabled: true` в конфиге
2. `visual_markers.enabled: true` в конфиге
3. Page объект передан в `VisualMarkers` корректно
4. JavaScript не блокируется на странице

**Q: Как изменить цвета визуальных маркеров?**

A: Редактируйте CSS в [src/utils/visual_markers.py](../src/utils/visual_markers.py:23) в методе `inject_styles()`.

## Дальнейшее развитие

Планируемые улучшения:

- [ ] Context manager для автоматической очистки маркеров
- [ ] Запись actions в видео-лог
- [ ] Экспорт в GIF анимацию
- [ ] Интеграция с pytest для тестов UI
- [ ] Websocket stream для удалённого просмотра
- [ ] Dashboard для мониторинга в реальном времени
