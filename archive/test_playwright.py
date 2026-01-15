import asyncio
from playwright.async_api import async_playwright

async def test_browser():
    async with async_playwright() as p:
        # Запускаем браузер (headless=False чтобы видеть что происходит)
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        
        # Идём на Яндекс
        await page.goto('https://ya.ru')
        
        # Делаем скриншот
        await page.screenshot(path='test.png')
        
        # Получаем заголовок
        title = await page.title()
        print(f"Заголовок страницы: {title}")
        
        # Ждём 3 секунды чтобы посмотреть
        await asyncio.sleep(3)
        
        await browser.close()

# Запускаем
asyncio.run(test_browser())