"""
AI Browser Agent - универсальный агент для автоматизации браузера

Использование:
    python main.py [--demo-mode] [--sandbox]

Опции:
    --demo-mode    Включить режим демонстрации с задержками и визуальными маркерами
    --sandbox      Умный режим анализа: воспроизводит ошибки из production,
                   генерирует тестовые сценарии и ищет решения

Примеры задач:
    - "Закажи пиццу на 4 человека"
    - "Найди вакансии Python разработчика в Москве"
    - "Удали спам из почты"

Workflow:
    1. Запустите агента: python main.py
       → Агент работает, SupervisorAgent фиксирует ошибки в data/errors/

    2. Проанализируйте ошибки: python main.py --sandbox
       → Sandbox генерирует тесты из реальных ошибок и ищет решения
"""
import asyncio
import sys
import argparse
from src.dialogue_manager import DialogueManager
from src.system_check import run_system_check
from src.version_info import print_version_info
from src.utils.demo_mode import initialize_demo_mode

async def main(demo_mode: bool = False, sandbox_mode: bool = False):
    """Точка входа в приложение"""
    # Инициализация demo mode
    if demo_mode:
        initialize_demo_mode(enabled=True)

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
    await manager.start(sandbox_mode=sandbox_mode)

if __name__ == "__main__":
    # Парсинг аргументов командной строки
    parser = argparse.ArgumentParser(
        description="AI Browser Agent - автоматизация браузера с помощью ИИ"
    )
    parser.add_argument(
        "--demo-mode",
        action="store_true",
        help="Включить режим демонстрации с задержками и визуальными маркерами"
    )
    parser.add_argument(
        "--sandbox",
        action="store_true",
        help="Умный режим анализа: воспроизводит ошибки из production и ищет решения"
    )
    args = parser.parse_args()

    try:
        asyncio.run(main(demo_mode=args.demo_mode, sandbox_mode=args.sandbox))
    except KeyboardInterrupt:
        print("\n\n👋 Программа завершена.")
    except Exception as e:
        print(f"\n\n❌ Критическая ошибка: {e}")
        print("Проверьте логи в папке logs/ для детальной информации.\n")
        sys.exit(1)
