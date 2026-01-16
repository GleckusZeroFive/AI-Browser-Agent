"""
Тестовый скрипт для проверки работы обработки капчи

Использование:
    python test_captcha.py

Скрипт открывает тестовые страницы с капчей и проверяет:
1. Детектирование капчи
2. Ожидание ручного решения
3. Автоматическое продолжение работы
"""

import asyncio
import sys
from pathlib import Path

# Добавляем путь к модулям проекта
sys.path.insert(0, str(Path(__file__).parent))

from src.tools.browser_tools import BrowserTools


async def test_captcha_detection():
    """Тест детектирования капчи на разных сайтах"""

    print("\n" + "="*70)
    print("🧪 Тест системы обработки капчи")
    print("="*70 + "\n")

    tools = BrowserTools()

    # Запускаем браузер
    print("🚀 Запуск браузера с антидетект защитой...")
    result = await tools.start_browser(headless=False)

    if result["status"] != "success":
        print(f"❌ Ошибка запуска браузера: {result['message']}")
        return

    print(f"✅ {result['message']}\n")

    # Тестовые сайты с капчей
    test_sites = [
        {
            "name": "Google reCAPTCHA v2 Demo",
            "url": "https://www.google.com/recaptcha/api2/demo",
            "description": "Тестовая страница Google с reCAPTCHA v2"
        },
        {
            "name": "hCaptcha Demo",
            "url": "https://accounts.hcaptcha.com/demo",
            "description": "Демо hCaptcha"
        }
    ]

    for i, site in enumerate(test_sites, 1):
        print(f"\n{'='*70}")
        print(f"📝 Тест {i}/{len(test_sites)}: {site['name']}")
        print(f"🌐 URL: {site['url']}")
        print(f"📄 {site['description']}")
        print('='*70 + "\n")

        # Переходим на сайт
        print(f"⏳ Переход на {site['name']}...")
        nav_result = await tools.navigate(site["url"])

        if nav_result["status"] != "success":
            print(f"❌ Ошибка навигации: {nav_result['message']}\n")
            continue

        print(f"✅ Страница загружена: {nav_result['title']}")

        # Проверяем капчу
        if nav_result.get("captcha_encountered"):
            print(f"\n🔍 Капча была обнаружена автоматически!")

            if nav_result.get("captcha_solved"):
                print(f"✅ Капча решена успешно!")
            else:
                print(f"⚠️  Капча не решена")
        else:
            # Явная проверка
            print("\n🔍 Выполняем явную проверку капчи...")
            captcha_check = await tools.check_for_captcha()

            if captcha_check["captcha_detected"]:
                print(f"\n✅ Капча обнаружена!")
                print(f"   Тип: {captcha_check['captcha_type']}")
                print(f"   Сообщение: {captcha_check['message']}")

                # Предлагаем решить капчу
                user_input = input("\n❓ Хотите решить капчу вручную? (y/n): ").strip().lower()

                if user_input == 'y':
                    print("\n⏳ Ожидание решения капчи...")
                    solve_result = await tools.solve_captcha_manually(timeout=180)

                    if solve_result["captcha_solved"]:
                        print(f"\n✅ Капча решена за {solve_result['duration']:.1f}с!")
                    else:
                        print(f"\n❌ {solve_result['message']}")
                else:
                    print("⏭️  Пропускаем решение капчи")
            else:
                print("ℹ️  Капча не обнаружена на странице")

        # Пауза между тестами
        if i < len(test_sites):
            print("\n⏸️  Пауза 3 секунды перед следующим тестом...")
            await asyncio.sleep(3)

    # Завершение
    print("\n" + "="*70)
    print("✅ Все тесты завершены!")
    print("="*70 + "\n")

    # Закрываем браузер
    await tools.close_browser()
    print("🔒 Браузер закрыт\n")


async def test_simple_navigation():
    """Простой тест навигации на сайт с возможной капчей"""

    print("\n" + "="*70)
    print("🧪 Простой тест навигации с обработкой капчи")
    print("="*70 + "\n")

    tools = BrowserTools()

    # Запуск браузера
    print("🚀 Запуск браузера...")
    await tools.start_browser(headless=False)

    # Вводим URL от пользователя
    url = input("🌐 Введите URL для проверки (или Enter для тестового): ").strip()

    if not url:
        url = "https://www.google.com/recaptcha/api2/demo"
        print(f"   Используем тестовый URL: {url}")

    print(f"\n⏳ Переход на {url}...")
    result = await tools.navigate(url)

    print(f"\n📊 Результат:")
    print(f"   Статус: {result['status']}")
    print(f"   Сообщение: {result['message']}")

    if result.get("captcha_encountered"):
        print(f"   🔍 Капча: Обнаружена")
        print(f"   ✅ Решена: {'Да' if result.get('captcha_solved') else 'Нет'}")
    else:
        print(f"   🔍 Капча: Не обнаружена")

    # Держим браузер открытым
    input("\n⏸️  Нажмите Enter для закрытия браузера...")

    await tools.close_browser()
    print("🔒 Браузер закрыт\n")


async def main():
    """Главная функция"""
    print("\n🔐 Тестирование системы обработки капчи")
    print("\nВыберите тест:")
    print("1. Полный тест на демо-сайтах")
    print("2. Простой тест (свой URL)")
    print("3. Выход")

    choice = input("\nВаш выбор (1-3): ").strip()

    if choice == "1":
        await test_captcha_detection()
    elif choice == "2":
        await test_simple_navigation()
    elif choice == "3":
        print("👋 До свидания!")
    else:
        print("❌ Неверный выбор")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Прервано пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
