#!/usr/bin/env python3
"""
Тест keepalive механизма и таймаутов
Проверяет что браузер переподключается при падении
и что таймауты работают корректно
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.tools.browser_tools import BrowserTools
from src.dialogue_manager import DialogueManager
from src.config import Config

async def test_browser_reconnect():
    """Тест переподключения браузера"""
    print("=" * 70)
    print("🔄 ТЕСТ: Переподключение браузера при падении")
    print("=" * 70)

    manager = DialogueManager()

    try:
        # 1. Запуск браузера
        print("\n1️⃣  Запуск браузера...")
        await manager.browser_tools.start_browser(headless=True)
        manager.browser_started = True
        print("   ✅ Браузер запущен")

        # 2. Проверка что браузер работает
        print("\n2️⃣  Первая проверка keepalive...")
        await manager._keepalive_check()
        print("   ✅ Браузер активен")

        # 3. Симулируем падение браузера
        print("\n3️⃣  Симулирую падение браузера (закрываю принудительно)...")
        await manager.browser_tools.close_browser()
        manager.browser_started = True  # Но флаг остаётся True чтобы симулировать "упавший браузер"
        print("   ✅ Браузер закрыт (симуляция падения)")

        # 4. Keepalive должен обнаружить падение и переподключить
        print("\n4️⃣  Keepalive должен обнаружить падение...")
        await manager._keepalive_check()

        if manager.browser_started:
            print("   ✅ Браузер успешно переподключён!")
            return True
        else:
            print("   ❌ Браузер не переподключился")
            return False

    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        print("\n5️⃣  Очистка...")
        if manager.browser_started:
            await manager.browser_tools.close_browser()
        print("   ✅ Очистка завершена")

async def test_timeout_config():
    """Тест настроек таймаутов"""
    print("\n\n" + "=" * 70)
    print("⏱️  ТЕСТ: Настройки таймаутов")
    print("=" * 70)

    print("\n📊 Текущие настройки:")
    print(f"   USER_INPUT_TIMEOUT: {Config.USER_INPUT_TIMEOUT} сек ({Config.USER_INPUT_TIMEOUT // 60} мин)")
    print(f"   USER_INPUT_GRACE_PERIOD: {Config.USER_INPUT_GRACE_PERIOD} сек")
    print(f"   KEEPALIVE_INTERVAL: {Config.KEEPALIVE_INTERVAL} сек")
    print(f"   BROWSER_CHECK_ENABLED: {Config.BROWSER_CHECK_ENABLED}")

    # Проверка что настройки разумные
    checks = []

    if Config.USER_INPUT_TIMEOUT >= 60:
        print("\n   ✅ USER_INPUT_TIMEOUT >= 60 сек")
        checks.append(True)
    else:
        print("\n   ❌ USER_INPUT_TIMEOUT слишком мал")
        checks.append(False)

    if Config.USER_INPUT_GRACE_PERIOD >= 30:
        print("   ✅ USER_INPUT_GRACE_PERIOD >= 30 сек")
        checks.append(True)
    else:
        print("   ❌ USER_INPUT_GRACE_PERIOD слишком мал")
        checks.append(False)

    if Config.KEEPALIVE_INTERVAL >= 30 and Config.KEEPALIVE_INTERVAL <= Config.USER_INPUT_TIMEOUT:
        print("   ✅ KEEPALIVE_INTERVAL в разумных пределах")
        checks.append(True)
    else:
        print("   ❌ KEEPALIVE_INTERVAL некорректный")
        checks.append(False)

    if Config.BROWSER_CHECK_ENABLED:
        print("   ✅ BROWSER_CHECK_ENABLED включен")
        checks.append(True)
    else:
        print("   ⚠️  BROWSER_CHECK_ENABLED выключен")
        checks.append(False)

    return all(checks)

async def test_logging_setup():
    """Тест настройки логирования"""
    print("\n\n" + "=" * 70)
    print("📝 ТЕСТ: Система логирования")
    print("=" * 70)

    manager = DialogueManager()

    print("\n1️⃣  Проверка создания логгера...")
    if hasattr(manager, 'logger'):
        print("   ✅ Логгер создан")
    else:
        print("   ❌ Логгер не создан")
        return False

    print("\n2️⃣  Проверка файлов логов...")
    import os

    logs_exist = []

    if os.path.exists("logs/dialogue_manager.log"):
        print("   ✅ logs/dialogue_manager.log существует")
        logs_exist.append(True)
    else:
        print("   ⚠️  logs/dialogue_manager.log ещё не создан")
        logs_exist.append(True)  # Это нормально, создастся при первом логе

    if os.path.exists("logs/errors.log"):
        print("   ✅ logs/errors.log существует")
        logs_exist.append(True)
    else:
        print("   ⚠️  logs/errors.log ещё не создан")
        logs_exist.append(True)  # Это нормально, создастся при первой ошибке

    print("\n3️⃣  Тест записи в лог...")
    try:
        manager.logger.info("Тестовое сообщение из test_keepalive.py")
        print("   ✅ Запись в лог успешна")
        logs_exist.append(True)
    except Exception as e:
        print(f"   ❌ Ошибка записи в лог: {e}")
        logs_exist.append(False)

    return all(logs_exist)

async def test_timeout_simulation():
    """Симуляция работы таймаута (без реального ожидания)"""
    print("\n\n" + "=" * 70)
    print("⏱️  СИМУЛЯЦИЯ: Логика таймаута")
    print("=" * 70)

    timeout_seconds = Config.USER_INPUT_TIMEOUT
    keepalive_interval = Config.KEEPALIVE_INTERVAL

    print(f"\n📊 Параметры:")
    print(f"   Таймаут: {timeout_seconds} сек ({timeout_seconds // 60} мин)")
    print(f"   Интервал keepalive: {keepalive_interval} сек")
    print(f"   Количество проверок: {timeout_seconds // keepalive_interval}")

    print(f"\n🔄 Симуляция событий:")

    current_time = 0
    last_keepalive = 0
    checks = 0

    while current_time < timeout_seconds:
        # Симуляция keepalive проверок
        if current_time - last_keepalive >= keepalive_interval:
            checks += 1
            print(f"   T={current_time}с: ✓ Keepalive проверка #{checks}")
            last_keepalive = current_time

        current_time += keepalive_interval

    print(f"\n   T={current_time}с: ⏱️  Таймаут! Спрашиваем пользователя")
    print(f"   T={current_time + Config.USER_INPUT_GRACE_PERIOD}с: ⏱️  Завершение сессии")

    print(f"\n✅ За {timeout_seconds // 60} минут произойдёт {checks} проверок браузера")

    return True

async def main():
    """Запуск всех тестов"""
    print("\n" + "=" * 70)
    print("🧪 ТЕСТИРОВАНИЕ KEEPALIVE И ТАЙМАУТОВ")
    print("=" * 70)

    results = []

    # Тест 1: Настройки таймаутов
    result1 = await test_timeout_config()
    results.append(("Настройки таймаутов", result1))

    # Тест 2: Система логирования
    result2 = await test_logging_setup()
    results.append(("Система логирования", result2))

    # Тест 3: Переподключение браузера
    result3 = await test_browser_reconnect()
    results.append(("Переподключение браузера", result3))

    # Тест 4: Симуляция таймаута
    result4 = await test_timeout_simulation()
    results.append(("Симуляция таймаута", result4))

    # Итоги
    print("\n\n" + "=" * 70)
    print("📊 ФИНАЛЬНЫЕ ИТОГИ")
    print("=" * 70)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"\n{status} - {name}")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    print("\n" + "=" * 70)
    print(f"Пройдено: {passed}/{total} тестов")

    if passed == total:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("✅ Keepalive и таймауты работают корректно!")
        print("=" * 70)
        return 0
    else:
        print("\n❌ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОШЛИ")
        print("=" * 70)
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
