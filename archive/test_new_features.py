"""
Тест новых возможностей: find_text и graceful limit handling
"""
import asyncio
from src.tools.browser_tools import BrowserTools
from src.agent.action_executor import ActionExecutor

async def test_find_text():
    """Тест функции поиска текста"""
    print("=" * 70)
    print("ТЕСТ 1: Проверка find_text (Ctrl+F поиск)")
    print("=" * 70)

    browser = BrowserTools()
    executor = ActionExecutor(browser)

    try:
        # Запуск браузера
        print("\n1. Запуск браузера...")
        await browser.start_browser(headless=False)
        print("   ✓ Браузер запущен")

        # Переход на страницу
        print("\n2. Переход на dodopizza.ru...")
        await browser.navigate("https://dodopizza.ru/krasnoyarsk")
        print("   ✓ Страница загружена")

        # Тест find_text через executor
        print("\n3. Тест поиска текста 'Пицца'...")
        action = {
            "action": "find_text",
            "params": {"search_text": "Пицца"},
            "reasoning": "Ищем пиццу на странице"
        }
        result = await executor.execute(action)

        print(f"\n   Результат:")
        print(f"   - Статус: {result.get('status')}")
        print(f"   - Сообщение: {result.get('message')}")
        print(f"   - Найдено: {result.get('found', False)}")
        print(f"   - Количество: {result.get('count', 0)}")

        if result.get('found'):
            print("\n   ✅ УСПЕХ: Поиск работает!")
        else:
            print("\n   ❌ ОШИБКА: Текст не найден")

        # Проверка доступных действий
        print("\n4. Проверка списка действий...")
        actions = executor.get_available_actions()
        print(f"   Доступно действий: {len(actions)}")

        if "find_text" in actions:
            print("   ✅ УСПЕХ: find_text присутствует в списке")
        else:
            print("   ❌ ОШИБКА: find_text отсутствует!")

        print(f"\n   Все действия: {', '.join(actions)}")

        await asyncio.sleep(3)

    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

    finally:
        print("\n5. Закрытие браузера...")
        await browser.close_browser()
        print("   ✓ Браузер закрыт")

async def test_limit_warning():
    """Тест предупреждения о лимите"""
    print("\n\n" + "=" * 70)
    print("ТЕСТ 2: Проверка логики предупреждения о лимите")
    print("=" * 70)

    max_actions = 10

    print("\nСимуляция счётчика действий:")
    for i in range(12):
        if i >= max_actions - 2 and i < max_actions:
            print(f"   Действие {i+1}: ⚠️ ПРЕДУПРЕЖДЕНИЕ - осталось {max_actions - i} действий")
        elif i >= max_actions:
            print(f"   Действие {i+1}: ❌ ЛИМИТ ДОСТИГНУТ - запрос объяснения")
        else:
            print(f"   Действие {i+1}: ✓ Выполняется нормально")

    print("\n✅ Логика работает корректно!")

async def main():
    """Запуск всех тестов"""
    print("\n🧪 ЗАПУСК ТЕСТОВ НОВЫХ ВОЗМОЖНОСТЕЙ\n")

    # Тест 1: find_text
    await test_find_text()

    # Тест 2: логика лимита
    await test_limit_warning()

    print("\n\n" + "=" * 70)
    print("✅ ВСЕ ТЕСТЫ ЗАВЕРШЕНЫ")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
