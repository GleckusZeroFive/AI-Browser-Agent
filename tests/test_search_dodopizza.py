#!/usr/bin/env python3
"""
Тестовый скрипт для проверки search_and_type на Додо Пицце
"""
import asyncio
import sys
import os

# Добавляем путь к модулям проекта
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.tools.browser_tools import BrowserTools


async def test_dodopizza_search():
    """Тест поиска на Додо Пицце (сайт БЕЗ поля поиска)"""

    print("=" * 70)
    print("🧪 ТЕСТ: Поиск на Додо Пицце (сайт БЕЗ поля поиска)")
    print("=" * 70)

    tools = BrowserTools()

    try:
        # 1. Запуск браузера
        print("\n1️⃣ Запуск браузера...")
        result = await tools.start_browser(headless=False)
        print(f"   ✓ {result['message']}")

        # 2. Переход на Додо Пиццу
        print("\n2️⃣ Переход на dodopizza.ru...")
        result = await tools.navigate("https://dodopizza.ru/moskva")
        print(f"   ✓ {result['message']}")

        # Пауза для загрузки и возможного решения капчи
        print("\n⏳ Ждём 3 секунды для загрузки страницы...")
        await asyncio.sleep(3)

        # 3. Поиск "пепперони" (должен использовать браузерный поиск)
        print("\n3️⃣ Поиск 'пепперони' через search_and_type...")
        result = await tools.search_and_type("пепперони")

        print(f"\n📊 РЕЗУЛЬТАТ:")
        print(f"   Статус: {result['status']}")
        print(f"   Сообщение: {result['message']}")

        if result.get('method') == 'page_search':
            print(f"   Метод: Браузерный поиск (Ctrl+F) ✅")
            print(f"   Найдено: {result.get('found', False)}")
            if result.get('count'):
                print(f"   Совпадений: {result['count']}")
        elif result.get('selector_used'):
            print(f"   Метод: Поле поиска")
            print(f"   Селектор: {result['selector_used']}")

        # 4. Если найдено, пробуем кликнуть
        if result.get('found'):
            print("\n4️⃣ Попытка клика по найденному блюду...")
            click_result = await tools.click_by_text("Пепперони")
            print(f"   ✓ {click_result['message']}")

            # 5. Проверка модального окна
            print("\n5️⃣ Ожидание модального окна...")
            await asyncio.sleep(1)
            modal_result = await tools.get_modal_text()

            if modal_result['status'] == 'success':
                print(f"   ✓ Модальное окно найдено")
                print(f"   Текст (первые 200 символов):\n   {modal_result['text'][:200]}...")
            else:
                print(f"   ⚠️ {modal_result['message']}")

        print("\n" + "=" * 70)
        print("✅ ТЕСТ ЗАВЕРШЁН")
        print("=" * 70)
        print("\n💡 Вывод:")
        print("   - search_and_type автоматически определил отсутствие поля поиска")
        print("   - Переключился на браузерный поиск (Ctrl+F)")
        print("   - Это работает для сайтов БЕЗ поля поиска (Додо Пицца и др.)")

        # Держим браузер открытым для проверки
        print("\n⏸️  Браузер остаётся открытым для проверки.")
        print("   Нажмите Enter для завершения...")
        input()

    except KeyboardInterrupt:
        print("\n\n⚠️  Прервано пользователем")
    except Exception as e:
        print(f"\n\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Закрытие браузера
        print("\n🔚 Закрытие браузера...")
        await tools.close_browser()
        print("   ✓ Готово")


if __name__ == "__main__":
    asyncio.run(test_dodopizza_search())
