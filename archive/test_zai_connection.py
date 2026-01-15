"""
Тест подключения к Z.AI API
"""
from src.agent.ai_agent import AIAgent

def test_zai_connection():
    """Простой тест подключения к Z.AI"""
    print("Инициализация AI агента с Z.AI...")
    agent = AIAgent()
    agent.add_system_prompt()

    print("Отправка тестового сообщения...")
    response = agent.chat("Привет! Представься пожалуйста.")

    print("\nОтвет от Z.AI:")
    print(response)
    print("\n✓ Подключение к Z.AI работает!")

if __name__ == "__main__":
    test_zai_connection()
