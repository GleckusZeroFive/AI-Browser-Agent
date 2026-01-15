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
import sys
from src.dialogue_manager import DialogueManager
from src.system_check import run_system_check
from src.version_info import print_version_info

async def main():
    """Точка входа в приложение"""
    # Проверка системных требований
    print("=" * 70)
    print("🚀 AI BROWSER AGENT - ЗАПУСК")
    print("=" * 70)

    # Вывод версий библиотек
    print_version_info(verbose=False)

    # Проверка системы
    if not run_system_check():
        print("\n❌ Запуск невозможен из-за проблем с системными требованиями.")
        print("Исправьте указанные проблемы и запустите программу снова.\n")
        sys.exit(1)

    # Запуск агента
    manager = DialogueManager()
    await manager.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Программа завершена.")
    except Exception as e:
        print(f"\n\n❌ Критическая ошибка: {e}")
        print("Проверьте логи в папке logs/ для детальной информации.\n")
        sys.exit(1)
