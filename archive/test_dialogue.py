"""
Тест диалоговой системы
Проверяем работу в интерактивном режиме
"""
import asyncio
from src.dialogue_manager import DialogueManager

async def test_dialogue():
    """Запуск теста диалога"""
    print("="*70)
    print("ТЕСТ ДИАЛОГОВОЙ СИСТЕМЫ")
    print("="*70)
    print("\nЭто тест работы диалога с AI агентом.")
    print("Введите запрос или 'exit' для выхода.\n")

    manager = DialogueManager()
    await manager.start()

if __name__ == "__main__":
    asyncio.run(test_dialogue())
