# Demo Mode - Пример использования

Этот пример демонстрирует все возможности Demo Mode на практическом сценарии.

## Что демонстрирует пример

1. **Логирование выполнения** - каждое действие логируется с деталями
2. **Визуальные маркеры** - подсветка элементов, индикаторы действий
3. **Задержки между действиями** - замедленное выполнение для наглядности
4. **Показ кода** - отображение выполняемых функций

## Запуск примера

### Обычный режим (без Demo Mode)

```bash
python examples/demo_mode_example.py
```

Выполнение происходит на обычной скорости без визуальных эффектов.

### Demo Mode

```bash
python examples/demo_mode_example.py --demo
```

Включается:
- Задержки между действиями
- Визуальные маркеры в браузере
- Показ выполняемого кода
- Детальное логирование

### Headless режим

```bash
python examples/demo_mode_example.py --demo --headless
```

Браузер работает в фоновом режиме (без окна).

## Просмотр логов в реальном времени

Откройте второй терминал и запустите log viewer:

```bash
# Терминал 1: Запуск примера
python examples/demo_mode_example.py --demo

# Терминал 2: Просмотр логов
python log_viewer.py
```

Log viewer будет показывать:
- ⏯️  START - начало выполнения функции
- ✅ SUCCESS - успешное завершение
- ❌ ERROR - ошибки
- Время выполнения каждой функции
- Аргументы функций

## Сценарий примера

Пример выполняет следующие действия:

1. **Открывает Wikipedia** (`open_website`)
   - Показывает индикатор "Открытие https://www.wikipedia.org"
   - Ждёт загрузки страницы

2. **Вводит поисковый запрос** (`search_text`)
   - Показывает индикатор "Поиск: Artificial Intelligence"
   - Анимация ввода текста (зелёная рамка + мигающий курсор)

3. **Нажимает Enter** для поиска
   - Ждёт загрузки результатов

4. **Скроллит страницу вниз** (`scroll_page`)
   - Показывает индикатор "⬇️ Скролл down"
   - Прокручивает на 500 пикселей

5. **Ещё скролл вниз**

6. **Скролл обратно вверх** (`scroll_page`)
   - Показывает индикатор "⬆️ Скролл up"

## Визуальные эффекты

### Индикатор действия
Синий баннер сверху страницы с описанием текущего действия:
```
🤖 Открытие https://www.wikipedia.org
```

### Подсветка ввода
Зелёная рамка вокруг поля ввода + мигающий курсор справа.

### Индикатор скролла
Плавающий badge справа с направлением:
```
⬇️ Скролл down
```

## Код примера

### Структура

```python
@demo_async_action
async def open_website(page, url: str):
    """Открыть веб-сайт"""
    demo = get_demo_mode()
    markers = get_visual_markers(page, enabled=demo.enabled)

    if demo.enabled:
        await markers.show_action_indicator(f"Открытие {url}", duration=2000)

    await page.goto(url)
    await page.wait_for_load_state("networkidle")
```

### Ключевые моменты

1. **Декоратор `@demo_async_action`**
   - Автоматически добавляет логирование
   - Показывает код функции перед выполнением
   - Делает задержки

2. **Проверка `if demo.enabled`**
   - Визуальные маркеры только в demo mode
   - Не влияет на production

3. **Использование `markers`**
   - `show_action_indicator()` - баннер с описанием
   - `show_typing()` - анимация ввода
   - `show_scroll_indicator()` - индикатор скролла

## Настройка под свои нужды

### Изменить задержки

Отредактируйте [demo_config.yaml](../demo_config.yaml):

```yaml
demo_mode:
  delays:
    before_action: 2.0  # Увеличить до 2 секунд
    after_action: 1.0   # Увеличить до 1 секунды
```

### Отключить визуальные маркеры

```yaml
demo_mode:
  visual_markers:
    enabled: false
```

### Изменить уровень логирования

```yaml
demo_mode:
  logging:
    level: minimal  # minimal, normal, verbose
```

## Запись скринкаста

### Setup для записи

1. **Запустите log viewer в левой половине экрана:**
   ```bash
   python log_viewer.py
   ```

2. **Запустите пример с demo mode:**
   ```bash
   python examples/demo_mode_example.py --demo
   ```
   Браузер откроется справа.

3. **Настройте OBS Studio:**
   - Источник 1: терминал с log viewer (левая половина)
   - Источник 2: браузер Firefox (правая половина)

4. **Начните запись** и выполните действия.

### Результат

Получите видео в split-screen режиме:
- Слева: логи в реальном времени с цветовой подсветкой
- Справа: браузер с визуальными индикаторами

## Использование в своих проектах

Скопируйте паттерн из примера:

```python
from src.utils.demo_mode import demo_async_action, get_demo_mode
from src.utils.visual_markers import get_visual_markers

@demo_async_action
async def my_action(page, param):
    """Моё действие"""
    demo = get_demo_mode()
    markers = get_visual_markers(page, enabled=demo.enabled)

    if demo.enabled:
        await markers.show_action_indicator("Описание действия")

    # Ваш код
    await page.click("selector")

    if demo.enabled:
        await demo.delay("after_action")
```

## Troubleshooting

### Браузер не открывается

```bash
# Установите Firefox для Playwright
playwright install firefox
```

### Визуальные маркеры не показываются

Проверьте в [demo_config.yaml](../demo_config.yaml):
```yaml
demo_mode:
  enabled: false  # <- Должно быть true для постоянного использования
```

Или запускайте с флагом `--demo`.

### Log viewer не видит логи

Убедитесь что папка `logs/` существует:
```bash
mkdir -p logs
```

### Ошибка импорта модулей

Запускайте из корневой директории проекта:
```bash
cd /path/to/ai-browser-agent
python examples/demo_mode_example.py --demo
```

## Дополнительные ресурсы

- [Документация Demo Mode для разработчиков](../docs/DEMO_MODE.md)
- [README проекта](../README.md#demo-mode)
- [Конфигурация Demo Mode](../demo_config.yaml)
