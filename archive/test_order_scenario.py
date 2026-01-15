import asyncio
from src.tools.browser_tools import BrowserTools

async def test_order_pizza():
    """Тестируем сценарий заказа пиццы"""
    
    tools = BrowserTools()
    
    print("=== ТЕСТ ЗАКАЗА ПИЦЦЫ ===\n")
    
    # Шаг 1: Открываем сайт
    print("1. Запускаем браузер и открываем Додо...")
    await tools.start_browser(headless=False)
    await tools.navigate("https://dodopizza.ru/krasnoyarsk")
    await asyncio.sleep(3)
    await tools.take_screenshot("screenshots/step1_main.png")
    
    # Шаг 2: Кликаем на комбо "2 пиццы"
    print("\n2. Ищем и кликаем по '2 пиццы'...")
    result = await tools.click_by_text("2 пиццы")
    print(result)
    await asyncio.sleep(2)
    await tools.take_screenshot("screenshots/step2_modal_opened.png")
    
    # Шаг 3: Ждём открытия модалки
    print("\n3. Ждём появления кнопки 'В корзину'...")
    result = await tools.wait_for_text("В корзину", timeout=5000)
    print(result)
    
    print("\nСМОТРИ НА ЭКРАН - открылась модалка с выбором пицц?")
    await asyncio.sleep(10)
    
    # Шаг 4: Нажимаем "В корзину" (не меняя состав)
    print("\n4. Кликаем 'В корзину'...")
    result = await tools.click_by_text("В корзину")
    print(result)
    await asyncio.sleep(2)
    await tools.take_screenshot("screenshots/step3_delivery_dialog.png")
    
    # Шаг 5: Должен появиться выбор доставки
    print("\n5. Проверяем появился ли выбор доставки...")
    result = await tools.wait_for_text("Указать адрес доставки", timeout=5000)
    print(result)
    
    print("\nСМОТРИ - появился выбор доставки?")
    await asyncio.sleep(10)
    
    # Шаг 6: Выбираем "Указать адрес доставки"
    print("\n6. Кликаем 'Указать адрес доставки'...")
    result = await tools.click_by_text("Указать адрес доставки")
    print(result)
    await asyncio.sleep(3)
    await tools.take_screenshot("screenshots/step4_address.png")
    
    print("\n7. Что показывается на экране сейчас?")
    print("Смотрим 15 секунд...")
    await asyncio.sleep(15)
    
    print("\n8. Закрываем браузер...")
    await tools.close_browser()
    
    print("\n=== ТЕСТ ЗАВЕРШЁН ===")
    print("Проверь скриншоты в screenshots/")

asyncio.run(test_order_pizza())