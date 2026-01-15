"""
AI Browser Agent - универсальный агент для автоматизации браузера

Использование:
    python main.py

Примеры задач:
    - "Закажи пиццу на 4 человека"
    - "Найди вакансии Python разработчика в Москве"
    - "Удали спам из почты"
"""
import asyncio
from src.dialogue_manager import DialogueManager

async def main():
    """Точка входа в приложение"""
    manager = DialogueManager()
    await manager.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Программа завершена.")
