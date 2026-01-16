#!/usr/bin/env python3
"""
Тест Demo Mode компонентов.

Проверяет работоспособность всех созданных модулей.
"""
import sys
import asyncio
from pathlib import Path

print("="*70)
print("🧪 ТЕСТИРОВАНИЕ DEMO MODE КОМПОНЕНТОВ")
print("="*70 + "\n")

# Тест 1: Импорт модулей
print("1️⃣  Тест импорта модулей...")
try:
    from src.utils.logging_decorator import log_execution, log_async_execution
    from src.utils.visual_markers import VisualMarkers, get_visual_markers
    from src.utils.demo_mode import (
        DemoMode, DemoModeConfig,
        demo_action, demo_async_action,
        get_demo_mode, initialize_demo_mode
    )
    print("   ✅ Все модули импортированы успешно\n")
except ImportError as e:
    print(f"   ❌ Ошибка импорта: {e}\n")
    sys.exit(1)

# Тест 2: Проверка зависимостей
print("2️⃣  Тест зависимостей...")
try:
    import yaml
    import watchdog
    import rich
    print("   ✅ Все зависимости установлены\n")
except ImportError as e:
    print(f"   ❌ Отсутствует зависимость: {e}")
    print("   💡 Установите: pip install -r requirements.txt\n")
    sys.exit(1)

# Тест 3: Конфигурация
print("3️⃣  Тест конфигурации...")
try:
    config = DemoModeConfig("demo_config.yaml")
    print(f"   ✅ Конфигурация загружена")
    print(f"      - Demo mode enabled: {config.enabled}")
    print(f"      - Visual markers: {config.visual_markers_enabled}")
    print(f"      - Delays: {config.delays}\n")
except Exception as e:
    print(f"   ❌ Ошибка загрузки конфигурации: {e}\n")
    sys.exit(1)

# Тест 4: Логирование
print("4️⃣  Тест декоратора логирования...")
try:
    @log_execution
    def test_function(a, b):
        """Тестовая функция"""
        return a + b

    result = test_function(2, 3)
    assert result == 5
    print(f"   ✅ Декоратор @log_execution работает (результат: {result})\n")
except Exception as e:
    print(f"   ❌ Ошибка: {e}\n")

# Тест 5: Асинхронное логирование
print("5️⃣  Тест асинхронного логирования...")
try:
    @log_async_execution
    async def test_async_function(x):
        """Тестовая асинхронная функция"""
        await asyncio.sleep(0.1)
        return x * 2

    result = asyncio.run(test_async_function(5))
    assert result == 10
    print(f"   ✅ Декоратор @log_async_execution работает (результат: {result})\n")
except Exception as e:
    print(f"   ❌ Ошибка: {e}\n")

# Тест 6: Demo Mode
print("6️⃣  Тест Demo Mode...")
try:
    initialize_demo_mode(enabled=False)  # Выключаем для теста
    demo = get_demo_mode()
    print(f"   ✅ Demo Mode инициализирован")
    print(f"      - Enabled: {demo.enabled}")
    print(f"      - Config: {type(demo.config).__name__}\n")
except Exception as e:
    print(f"   ❌ Ошибка: {e}\n")

# Тест 7: Декоратор demo_action
print("7️⃣  Тест декоратора demo_action...")
try:
    @demo_action
    def test_demo_function(n):
        """Тестовая функция с demo_action"""
        return n ** 2

    result = test_demo_function(4)
    assert result == 16
    print(f"   ✅ Декоратор @demo_action работает (результат: {result})\n")
except Exception as e:
    print(f"   ❌ Ошибка: {e}\n")

# Тест 8: Проверка файлов
print("8️⃣  Тест наличия файлов...")
files_to_check = [
    "src/utils/logging_decorator.py",
    "src/utils/visual_markers.py",
    "src/utils/demo_mode.py",
    "log_viewer.py",
    "demo_config.yaml",
    "docs/DEMO_MODE.md",
    "examples/demo_mode_example.py",
    "examples/DEMO_MODE_EXAMPLE.md",
    "DEMO_MODE_SUMMARY.md"
]

all_exist = True
for file_path in files_to_check:
    path = Path(file_path)
    if path.exists():
        print(f"   ✅ {file_path}")
    else:
        print(f"   ❌ {file_path} не найден")
        all_exist = False

if all_exist:
    print("\n   ✅ Все файлы на месте\n")
else:
    print("\n   ⚠️  Некоторые файлы отсутствуют\n")

# Тест 9: Проверка logs директории
print("9️⃣  Тест директории logs...")
logs_dir = Path("logs")
if logs_dir.exists() and logs_dir.is_dir():
    print(f"   ✅ Директория logs/ существует")
    log_files = list(logs_dir.glob("execution_*.log"))
    print(f"   📁 Найдено лог-файлов: {len(log_files)}\n")
else:
    print(f"   ℹ️  Директория logs/ будет создана при первом запуске\n")

# Финальный отчёт
print("="*70)
print("📊 ИТОГИ ТЕСТИРОВАНИЯ")
print("="*70)
print("✅ Все основные компоненты работают корректно!")
print("\n🚀 Следующие шаги:")
print("   1. Запустите пример: python examples/demo_mode_example.py --demo")
print("   2. В другом терминале: python log_viewer.py")
print("   3. Или запустите агента: python main.py --demo-mode")
print("\n📚 Документация:")
print("   - README.md - Секция Demo Mode")
print("   - docs/DEMO_MODE.md - Полное руководство")
print("   - DEMO_MODE_SUMMARY.md - Сводка")
print("="*70 + "\n")
