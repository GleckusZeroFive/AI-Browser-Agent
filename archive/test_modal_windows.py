#!/usr/bin/env python3
"""
Тест работы с модальными окнами на Dodo Pizza
Проверяем: открытие товара → чтение модального окна → закрытие
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.tools.browser_tools import BrowserTools
from src.agent.action_executor import ActionExecutor

async def test_modal_workflow():
    """Тест полного цикла работы с модальным окном"""
    print("=" * 70)
    print("🪟 ТЕСТ: Работа с модальными окнами")
    print("=" * 70)

    browser = BrowserTools()
    executor = ActionExecutor(browser)

    try:
        # 1. Запуск браузера
        print("\n1️⃣  Запуск браузера...")
        result = await browser.start_browser(headless=False)
        if result['status'] == 'success':
            print(f"   ✅ {result['message']}")
        else:
            print(f"   ❌ Ошибка: {result['message']}")
            return False

        # 2. Переход на сайт
        print("\n2️⃣  Переход на dodopizza.ru/krasnoyarsk...")
        result = await browser.navigate("https://dodopizza.ru/krasnoyarsk")
        if result['status'] == 'success':
            print(f"   ✅ {result['message']}")
        else:
            print(f"   ❌ Ошибка: {result['message']}")
            return False

        # Ждём загрузки
        await asyncio.sleep(3)

        # 3. Клик по первому товару (любая пицца)
        print("\n3️⃣  Клик по товару 'Морс'...")
        action = {
            "action": "click_by_text",
            "params": {"text": "Морс"},
            "reasoning": "Открываем карточку товара"
        }
        result = await executor.execute(action)

        if result['status'] == 'success':
            print(f"   ✅ {result['message']}")
        else:
            print(f"   ❌ Ошибка: {result['message']}")
            return False

        # 4. Ждём появления модального окна
        print("\n4️⃣  Ожидание модального окна...")
        action = {
            "action": "wait_for_modal",
            "params": {"timeout": 5000},
            "reasoning": "Ждём открытия модального окна"
        }
        result = await executor.execute(action)

        if result['status'] == 'success':
            print(f"   ✅ {result['message']}")
            print(f"   📍 Селектор: {result.get('selector', 'N/A')}")
        elif result['status'] == 'timeout':
            print(f"   ⚠️  {result['message']} - продолжаем")
        else:
            print(f"   ❌ Ошибка: {result['message']}")
            return False

        # Ждём немного для стабильности
        await asyncio.sleep(2)

        # 5. Чтение текста из модального окна
        print("\n5️⃣  Чтение текста из модального окна...")
        action = {
            "action": "get_modal_text",
            "params": {},
            "reasoning": "Читаем информацию о товаре"
        }
        result = await executor.execute(action)

        if result['status'] == 'success':
            text = result.get('text', '')
            length = result.get('length', 0)
            print(f"   ✅ Текст получен")
            print(f"   📏 Длина: {length} символов")
            print(f"\n   📄 Содержимое (первые 300 символов):")
            print(f"   {text[:300]}...")

            # Проверяем, что в тексте есть полезная информация
            if length > 50:
                print(f"\n   ✅ УСПЕХ! Модальное окно содержит информацию")
            else:
                print(f"\n   ⚠️  Мало текста, возможно окно не открылось")
                return False
        else:
            print(f"   ❌ Ошибка: {result['message']}")
            return False

        # Ждём перед закрытием
        print("\n   ⏱️  Ждём 2 секунды перед закрытием...")
        await asyncio.sleep(2)

        # 6. Закрытие модального окна
        print("\n6️⃣  Закрытие модального окна...")
        action = {
            "action": "close_modal",
            "params": {},
            "reasoning": "Закрываем модальное окно"
        }
        result = await executor.execute(action)

        if result['status'] == 'success' or result['status'] == 'warning':
            print(f"   ✅ {result['message']}")
            if 'method' in result:
                print(f"   🔧 Метод: {result['method']}")
        else:
            print(f"   ❌ Ошибка: {result['message']}")
            return False

        # Финальная пауза
        await asyncio.sleep(2)

        print("\n" + "=" * 70)
        print("✅ ТЕСТ ПРОЙДЕН УСПЕШНО!")
        print("=" * 70)
        print("\n📊 Проверено:")
        print("   ✅ Клик по товару")
        print("   ✅ Ожидание модального окна")
        print("   ✅ Чтение текста из модального окна")
        print("   ✅ Закрытие модального окна")
        print("=" * 70)

        return True

    except Exception as e:
        print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        print("\n7️⃣  Закрытие браузера...")
        await browser.close_browser()
        print("   ✅ Браузер закрыт")

async def test_actions_list():
    """Проверка списка действий"""
    print("\n\n" + "=" * 70)
    print("📋 ПРОВЕРКА: Список доступных действий")
    print("=" * 70)

    browser = BrowserTools()
    executor = ActionExecutor(browser)

    actions = executor.get_available_actions()
    print(f"\n📊 Всего действий: {len(actions)}")

    modal_actions = ['close_modal', 'wait_for_modal', 'get_modal_text']
    print(f"\n🪟 Проверка действий для модальных окон:")

    all_present = True
    for action in modal_actions:
        if action in actions:
            print(f"   ✅ {action}")
        else:
            print(f"   ❌ {action} - ОТСУТСТВУЕТ!")
            all_present = False

    if all_present:
        print(f"\n✅ Все действия для модальных окон добавлены!")
    else:
        print(f"\n❌ Не все действия присутствуют!")

    print(f"\n📝 Полный список действий:")
    for i, action in enumerate(actions, 1):
        marker = "🪟" if action in modal_actions else "  "
        print(f"   {marker} {i}. {action}")

    return all_present

async def main():
    """Запуск всех тестов"""
    print("\n" + "=" * 70)
    print("🧪 ТЕСТИРОВАНИЕ МОДАЛЬНЫХ ОКОН")
    print("=" * 70)

    results = []

    # Тест 1: Список действий
    print("\n")
    result1 = await test_actions_list()
    results.append(("Список действий", result1))

    # Тест 2: Реальный workflow
    print("\n")
    result2 = await test_modal_workflow()
    results.append(("Реальный workflow с модальным окном", result2))

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
        print("✅ Работа с модальными окнами реализована!")
        print("=" * 70)
        return 0
    else:
        print("\n❌ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОШЛИ")
        print("=" * 70)
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
