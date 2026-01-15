import asyncio
from src.tools.browser_tools import BrowserTools

async def test_order_v2():
    """Улучшенный тест заказа"""
    
    tools = BrowserTools()
    
    print("=== УЛУЧШЕННЫЙ ТЕСТ ЗАКАЗА ===\n")
    
    # Шаг 1: Открываем сайт
    print("1. Запускаем браузер...")
    await tools.start_browser(headless=False)
    
    print("2. Открываем Додо...")
    await tools.navigate("https://dodopizza.ru/krasnoyarsk")
    await asyncio.sleep(4)  # больше времени на загрузку
    
    print("3. Делаем скриншот главной...")
    result = await tools.take_screenshot("screenshots/v2_step1_main.png")
    print(result)
    
    # Шаг 2: Кликаем на "2 пиццы"
    print("\n4. Кликаем по '2 пиццы'...")
    result = await tools.click_by_text("2 пиццы")
    print(result)
    
    print("5. Ждём 3 секунды чтобы модалка открылась...")
    await asyncio.sleep(3)
    
    print("6. Скриншот модалки...")
    result = await tools.take_screenshot("screenshots/v2_step2_modal.png")
    print(result)
    
    # Шаг 3: Попробуем кликнуть по testid
    print("\n7. Пробуем кликнуть по кнопке через testid...")
    result = await tools.click_button_by_test_id("product__button")
    print(result)
    
    if result['status'] == 'error':
        print("\n8. testid не сработал, пробуем force click...")
        result = await tools.click_by_text_force("В корзину")
        print(result)
    
    print("\n9. Ждём 3 секунды...")
    await asyncio.sleep(3)
    
    print("10. Скриншот после клика...")
    result = await tools.take_screenshot("screenshots/v2_step3_after_cart.png")
    print(result)
    
    # Получим текст страницы чтобы понять что там
    print("\n11. Получаем текст страницы...")
    result = await tools.get_page_text()
    print(f"Длина текста: {result.get('full_length', 0)}")
    
    # Сохраним в файл
    with open("logs/after_cart_click.txt", "w", encoding="utf-8") as f:
        f.write(result.get('text', ''))
    print("Текст сохранён в logs/after_cart_click.txt")
    
    print("\n12. Смотрим на экран 20 секунд - ЧТО ТАМ?")
    await asyncio.sleep(20)
    
    print("\n13. Закрываем...")
    await tools.close_browser()
    
    print("\n=== ТЕСТ ЗАВЕРШЁН ===")
    print("\nПРОВЕРЬ:")
    print("1. screenshots/v2_step1_main.png - главная страница")
    print("2. screenshots/v2_step2_modal.png - открытая модалка")
    print("3. screenshots/v2_step3_after_cart.png - после клика в корзину")
    print("4. logs/after_cart_click.txt - текст страницы")

asyncio.run(test_order_v2())