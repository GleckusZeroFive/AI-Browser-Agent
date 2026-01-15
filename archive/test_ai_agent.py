import asyncio
from src.agent.ai_agent import AIAgent
from src.tools.browser_tools import BrowserTools

async def test_ai_agent():
    """Тестируем AI агента"""
    
    print("=== ТЕСТ AI АГЕНТА ===\n")
    
    # Создаём агента
    agent = AIAgent()
    agent.add_system_prompt()
    
    # Создаём browser tools
    tools = BrowserTools()
    
    print("1. Запускаем браузер...")
    await tools.start_browser(headless=False)
    
    print("\n2. Открываем Додо Пиццу...")
    await tools.navigate("https://dodopizza.ru/krasnoyarsk")
    await asyncio.sleep(3)
    
    print("\n3. Получаем текст страницы...")
    page_result = await tools.get_page_text()
    page_text = page_result.get('text', '')
    
    print(f"Получили {len(page_text)} символов текста")
    
    # Тестируем агента
    print("\n4. Спрашиваем у агента что он видит...")
    
    user_query = "Посмотри на страницу. Какие есть популярные позиции в меню?"
    
    response = agent.chat(user_query, context=page_text[:1500])  # первые 1500 символов
    
    print(f"\n🤖 AI Агент:\n{response}\n")
    
    # Второй вопрос
    print("\n5. Задаём второй вопрос...")
    user_query2 = "Посоветуй что-нибудь выгодное для компании из 3 человек"
    
    response2 = agent.chat(user_query2)
    
    print(f"\n🤖 AI Агент:\n{response2}\n")
    
    print("\n6. Ждём 10 секунд...")
    await asyncio.sleep(10)
    
    print("\n7. Закрываем браузер...")
    await tools.close_browser()
    
    print("\n=== ТЕСТ ЗАВЕРШЁН ===")

if __name__ == "__main__":
    asyncio.run(test_ai_agent())