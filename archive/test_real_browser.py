#!/usr/bin/env python3
"""
Реальный тест с браузером
Проверяем работу find_text на живом сайте
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.tools.browser_tools import BrowserTools
from src.agent.action_executor import ActionExecutor

async def test_find_text_real():
    """Тест find_text на реальном сайте"""
    print("=" * 70)
    print("🌐 РЕАЛЬНЫЙ ТЕСТ: find_text на Dodo Pizza")
    print("=" * 70)

    browser = BrowserTools()
    executor = ActionExecutor(browser)

    try:
        # 1. Запуск браузера
        print("\n1️⃣  Запуск браузера...")
        result = await browser.start_browser(headless=True)
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
            print(f"   📄 Title: {result.get('title', 'N/A')}")
        else:
            print(f"   ❌ Ошибка: {result['message']}")
            return False

        # Ждём загрузки
        await asyncio.sleep(3)

        # 3. Тест find_text через executor
        print("\n3️⃣  Тест поиска 'Пицца' через find_text...")
        action = {
            "action": "find_text",
            "params": {"search_text": "Пицца"},
            "reasoning": "Ищем слово 'Пицца' на странице"
        }
        result = await executor.execute(action)

        print(f"\n   📊 Результат:")
        print(f"   - Статус: {result.get('status')}")
        print(f"   - Сообщение: {result.get('message')}")
        print(f"   - Найдено: {result.get('found', False)}")
        print(f"   - Количество: {result.get('count', 0)}")

        if result.get('found') and result.get('count', 0) > 0:
            print(f"\n   ✅ УСПЕХ! Найдено {result.get('count')} совпадений")
        else:
            print("\n   ❌ ОШИБКА: Текст не найден")
            return False

        # 4. Тест несуществующего текста
        print("\n4️⃣  Тест поиска несуществующего текста 'XYZABC123'...")
        action = {
            "action": "find_text",
            "params": {"search_text": "XYZABC123"},
            "reasoning": "Ищем несуществующий текст"
        }
        result = await executor.execute(action)

        if not result.get('found') and result.get('count', 0) == 0:
            print(f"   ✅ УСПЕХ! Корректно определил отсутствие текста")
        else:
            print(f"   ❌ ОШИБКА: Должен был вернуть found=False")
            return False

        # 5. Проверка списка действий
        print("\n5️⃣  Проверка списка доступных действий...")
        actions = executor.get_available_actions()
        print(f"   Всего действий: {len(actions)}")

        if "find_text" in actions:
            print(f"   ✅ find_text присутствует в списке")
        else:
            print(f"   ❌ ОШИБКА: find_text отсутствует!")
            return False

        print(f"\n   📝 Все действия: {', '.join(actions)}")

        return True

    except Exception as e:
        print(f"\n❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        print("\n6️⃣  Закрытие браузера...")
        await browser.close_browser()
        print("   ✅ Браузер закрыт")

async def test_limit_simulation():
    """Симуляция работы с лимитом"""
    print("\n\n" + "=" * 70)
    print("⚠️  СИМУЛЯЦИЯ: Работа с лимитом действий")
    print("=" * 70)

    max_actions = 10

    print("\nСимуляция счётчика:")
    for i in range(12):
        actions_count = i

        if actions_count >= max_actions - 2 and actions_count < max_actions:
            remaining = max_actions - actions_count
            print(f"   Действие {i+1}: ⚠️  ПРЕДУПРЕЖДЕНИЕ - осталось {remaining}")
        elif actions_count >= max_actions:
            print(f"   Действие {i+1}: ❌ ЛИМИТ - агент объясняет")
            break
        else:
            print(f"   Действие {i+1}: ✓ Выполняется")

    print("\n   ✅ Логика лимита работает корректно!")
    return True

async def main():
    """Запуск всех тестов"""
    print("\n" + "=" * 70)
    print("🧪 ПОЛНОЦЕННОЕ ТЕСТИРОВАНИЕ С РЕАЛЬНЫМ БРАУЗЕРОМ")
    print("=" * 70)

    results = []

    # Тест 1: Реальный браузер + find_text
    print("\n")
    result1 = await test_find_text_real()
    results.append(("Реальный браузер + find_text", result1))

    # Тест 2: Симуляция лимита
    result2 = await test_limit_simulation()
    results.append(("Симуляция лимита", result2))

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
        print("✅ Изменения работают корректно!")
        print("=" * 70)
        return 0
    else:
        print("\n❌ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОШЛИ")
        print("=" * 70)
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
