# Установка Demo Mode

Пошаговое руководство по установке и настройке Demo Mode для AI Browser Agent.

## Предварительные требования

- Python 3.10 или выше
- pip (менеджер пакетов Python)
- Git (для клонирования репозитория)

## Шаги установки

### 1. Установка зависимостей

Demo Mode добавляет следующие новые зависимости:

```bash
pip install watchdog>=3.0.0    # Для отслеживания изменений в лог-файлах
pip install rich>=13.0.0       # Для красивого форматирования вывода
pip install pyyaml>=6.0.0      # Для парсинга конфигурации
```

Или установите все зависимости сразу:

```bash
pip install -r requirements.txt
```

### 2. Проверка установки

Запустите тестовый скрипт:

```bash
python3 test_demo_mode.py
```

Вы должны увидеть:

```
======================================================================
🧪 ТЕСТИРОВАНИЕ DEMO MODE КОМПОНЕНТОВ
======================================================================

1️⃣  Тест импорта модулей...
   ✅ Все модули импортированы успешно

2️⃣  Тест зависимостей...
   ✅ Все зависимости установлены

...

✅ Все основные компоненты работают корректно!
```

### 3. Настройка конфигурации

Отредактируйте [demo_config.yaml](demo_config.yaml) под свои нужды:

```yaml
demo_mode:
  enabled: false  # true для постоянного включения

  delays:
    before_action: 1.0    # Задержка перед действием (сек)
    after_action: 0.5     # Задержка после действия (сек)

  visual_markers:
    enabled: true
    highlight_clicks: true
    show_typing: true

  logging:
    level: verbose  # minimal, normal, verbose
```

## Быстрый тест

### Запуск примера

```bash
# Терминал 1: Log viewer
python3 log_viewer.py

# Терминал 2: Demo Mode пример
python3 examples/demo_mode_example.py --demo
```

Вы должны увидеть:
- В терминале 1: цветные логи в реальном времени
- В терминале 2: выполнение сценария с задержками
- В браузере Firefox: визуальные индикаторы и подсветку элементов

### Запуск агента

```bash
python3 main.py --demo-mode
```

## Troubleshooting

### Проблема: `ModuleNotFoundError: No module named 'watchdog'`

**Решение:**
```bash
pip install watchdog rich pyyaml
```

### Проблема: `FileNotFoundError: demo_config.yaml`

**Решение:**
Убедитесь, что запускаете из корневой директории проекта:
```bash
cd /path/to/ai-browser-agent
python3 log_viewer.py
```

### Проблема: Log viewer не показывает цвета

**Решение:**
Убедитесь, что терминал поддерживает цвета. Попробуйте:
```bash
export TERM=xterm-256color
python3 log_viewer.py
```

### Проблема: Визуальные маркеры не появляются в браузере

**Решение:**
1. Проверьте конфигурацию в [demo_config.yaml](demo_config.yaml):
   ```yaml
   visual_markers:
     enabled: true
   ```

2. Убедитесь, что запускаете с флагом `--demo` или `--demo-mode`

3. Проверьте, что JavaScript не блокируется на сайте

### Проблема: Логи не создаются

**Решение:**
Создайте директорию logs:
```bash
mkdir -p logs
```

## Проверка работоспособности

### Тест 1: Логирование

```bash
python3 -c "
from src.utils.logging_decorator import log_execution

@log_execution
def test():
    return 'OK'

print(test())
"
```

Ожидаемый вывод:
```
2024-01-15 12:30:00 | INFO | <stdin>:1 | test | ⏯️  START | test()
2024-01-15 12:30:00 | INFO | <stdin>:1 | test | ✅ SUCCESS | Duration: 0.000s | Result: 'OK'
OK
```

### Тест 2: Log Viewer

```bash
# Создайте тестовый лог
echo "2024-01-15 12:30:00 | INFO | test.py:10 | test_func | ⏯️  START | test_func()" > logs/execution_test.log

# Запустите viewer
python3 log_viewer.py logs/execution_test.log
```

### Тест 3: Demo Config

```bash
python3 -c "
from src.utils.demo_mode import DemoModeConfig
config = DemoModeConfig('demo_config.yaml')
print(f'Demo mode enabled: {config.enabled}')
print(f'Delays: {config.delays}')
"
```

## Дополнительная настройка

### OBS Studio (для записи скринкастов)

**Linux:**
```bash
sudo apt install obs-studio
```

**macOS:**
```bash
brew install obs
```

**Windows:**
Скачайте с [obsproject.com](https://obsproject.com)

### Настройка терминала для записи

Увеличьте шрифт для читаемости:
- Терминал GNOME: Preferences → Profile → Font → 14pt
- iTerm2 (macOS): Preferences → Profiles → Text → 14pt
- Windows Terminal: Settings → Appearance → Font size → 14

### Рекомендуемые настройки терминала

```bash
# В ~/.bashrc или ~/.zshrc
export PS1='\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ '
export TERM=xterm-256color
```

## Структура файлов после установки

```
ai-browser-agent/
├── src/
│   └── utils/
│       ├── logging_decorator.py    ✅ Создан
│       ├── visual_markers.py       ✅ Создан
│       └── demo_mode.py            ✅ Создан
├── logs/
│   └── execution_*.log             📝 Создаётся автоматически
├── docs/
│   └── DEMO_MODE.md                ✅ Создан
├── examples/
│   ├── demo_mode_example.py        ✅ Создан
│   └── DEMO_MODE_EXAMPLE.md        ✅ Создан
├── log_viewer.py                   ✅ Создан
├── demo_config.yaml                ✅ Создан
├── test_demo_mode.py               ✅ Создан
├── DEMO_MODE_SUMMARY.md            ✅ Создан
├── INSTALLATION_DEMO_MODE.md       ✅ Создан (этот файл)
├── main.py                         ✅ Обновлён
└── requirements.txt                ✅ Обновлён
```

## Следующие шаги

После успешной установки:

1. **Прочитайте документацию:**
   - [DEMO_MODE_SUMMARY.md](DEMO_MODE_SUMMARY.md) - краткая сводка
   - [docs/DEMO_MODE.md](docs/DEMO_MODE.md) - полное руководство для разработчиков
   - [README.md](README.md#demo-mode) - пользовательская документация

2. **Попробуйте пример:**
   ```bash
   python3 examples/demo_mode_example.py --demo
   ```

3. **Запустите агента в Demo Mode:**
   ```bash
   python3 main.py --demo-mode
   ```

4. **Настройте под себя:**
   - Измените задержки в [demo_config.yaml](demo_config.yaml)
   - Настройте визуальные маркеры
   - Выберите уровень логирования

5. **Запишите скринкаст:**
   - Следуйте инструкциям в [README.md](README.md#запись-скринкаста-в-split-screen-режиме)

## Полезные команды

```bash
# Просмотр последнего лог-файла
python3 log_viewer.py

# Просмотр конкретного лог-файла
python3 log_viewer.py logs/execution_20240115.log

# Запуск примера без браузера (headless)
python3 examples/demo_mode_example.py --demo --headless

# Запуск агента в Demo Mode
python3 main.py --demo-mode

# Тестирование компонентов
python3 test_demo_mode.py

# Просмотр конфигурации
cat demo_config.yaml
```

## Получение помощи

Если возникли проблемы:

1. Проверьте [Troubleshooting](#troubleshooting) выше
2. Запустите тесты: `python3 test_demo_mode.py`
3. Проверьте логи в `logs/execution_*.log`
4. Посмотрите документацию в `docs/DEMO_MODE.md`

---

Готово! Теперь у вас установлен и настроен Demo Mode для AI Browser Agent.
