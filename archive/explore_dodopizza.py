import asyncio
from src.tools.browser_tools import BrowserTools

async def explore_dodopizza():
    """Детально изучаем Додо Пиццу"""
    
    tools = BrowserTools()
    
    print("=== ИССЛЕДОВАНИЕ ДОДО ПИЦЦЫ ===\n")
    
    print("1. Запускаем браузер...")
    await tools.start_browser(headless=False)
    
    print("\n2. Открываем Додо...")
    result = await tools.navigate("https://dodopizza.ru/krasnoyarsk")
    print(result)
    
    print("\n3. Ждём загрузки...")
    await asyncio.sleep(3)
    
    print("\n4. Делаем скриншот главной...")
    await tools.take_screenshot("screenshots/dodo_1_main.png")
    
    print("\n5. Получаем текст главной страницы...")
    result = await tools.get_page_text()
    print(f"Длина текста: {result.get('full_length', 0)}")
    
    # Сохраним весь текст в файл для анализа
    with open("logs/dodo_main_text.txt", "w", encoding="utf-8") as f:
        f.write(result.get('text', ''))
    print("Текст сохранён в logs/dodo_main_text.txt")
    
    print("\n6. Попробуем кликнуть на первую пиццу...")
    print("Ждём 5 секунд - ПОСМОТРИ какие пиццы видны на экране!")
    await asyncio.sleep(5)
    
    # Попробуем найти и кликнуть на карточку пиццы
    try:
        # Додо обычно использует article или div для карточек
        print("\n7. Ищем карточки пицц...")
        
        # Сделаем скриншот с выделением элементов (для отладки)
        await tools.take_screenshot("screenshots/dodo_2_before_click.png")
        
        # Можно попробовать разные селекторы
        # Вариант 1: по тексту (если видно название пиццы)
        # Вариант 2: по CSS классу
        # Вариант 3: по data-атрибутам
        
        print("\nЖдём 30 секунд...")
        print("ВНИМАТЕЛЬНО СМОТРИ НА ЭКРАН:")
        print("- Какие кнопки есть на карточках пицц?")
        print("- Что происходит если навести мышкой?")
        print("- Есть ли кнопка 'В корзину' или 'Выбрать'?")
        await asyncio.sleep(30)
        
    except Exception as e:
        print(f"Ошибка при поиске элементов: {e}")
    
    print("\n8. Закрываем браузер...")
    await tools.close_browser()
    
    print("\n=== ИССЛЕДОВАНИЕ ЗАВЕРШЕНО ===")
    print("Проверь файлы:")
    print("- screenshots/dodo_1_main.png")
    print("- screenshots/dodo_2_before_click.png")
    print("- logs/dodo_main_text.txt")

asyncio.run(explore_dodopizza())