"""
Модуль проверки системных требований
Проверяет наличие необходимых компонентов перед запуском приложения
"""
import sys
import subprocess
import shutil
from pathlib import Path
from typing import Tuple, Optional


class SystemCheck:
    """Проверка системных требований и зависимостей"""

    @staticmethod
    def check_python_version() -> Tuple[bool, str]:
        """
        Проверить версию Python

        Returns:
            (success, message): результат проверки и сообщение
        """
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 10):
            return False, (
                f"❌ Требуется Python 3.10 или выше. "
                f"Текущая версия: {version.major}.{version.minor}.{version.micro}\n"
                f"Пожалуйста, обновите Python: https://www.python.org/downloads/"
            )
        return True, f"✓ Python {version.major}.{version.minor}.{version.micro}"

    @staticmethod
    def check_playwright_installation() -> Tuple[bool, str]:
        """
        Проверить установку Playwright

        Returns:
            (success, message): результат проверки и сообщение
        """
        try:
            import playwright
            return True, f"✓ Playwright {playwright.__version__}"
        except ImportError:
            return False, (
                "❌ Playwright не установлен\n"
                "Установите с помощью: pip install -r requirements.txt"
            )

    @staticmethod
    def check_firefox_browser() -> Tuple[bool, str]:
        """
        Проверить установку Firefox браузера для Playwright

        Playwright устанавливает браузеры в специальную директорию.
        Проверяем наличие Firefox в системе Playwright.

        Returns:
            (success, message): результат проверки и сообщение
        """
        try:
            # Пытаемся найти playwright в системе
            playwright_path = shutil.which("playwright")

            if not playwright_path:
                # Пытаемся запустить через Python модуль
                try:
                    result = subprocess.run(
                        [sys.executable, "-m", "playwright", "--version"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode != 0:
                        return False, (
                            "❌ Playwright CLI не найден\n"
                            "Установите с помощью: pip install playwright"
                        )
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    return False, (
                        "❌ Playwright CLI не найден\n"
                        "Установите с помощью: pip install playwright"
                    )

            # Проверяем установку Firefox через playwright CLI
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "playwright", "install", "--dry-run", "firefox"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                # Если dry-run прошёл успешно, проверяем наличие установленного браузера
                # Playwright хранит браузеры в ~/.cache/ms-playwright (Linux) или эквиваленте
                from pathlib import Path
                import os

                # Определяем путь к кэшу браузеров Playwright
                if sys.platform == "win32":
                    cache_path = Path(os.getenv("LOCALAPPDATA", "")) / "ms-playwright"
                elif sys.platform == "darwin":
                    cache_path = Path.home() / "Library" / "Caches" / "ms-playwright"
                else:  # Linux
                    cache_path = Path.home() / ".cache" / "ms-playwright"

                # Ищем Firefox в кэше
                firefox_found = False
                if cache_path.exists():
                    for item in cache_path.iterdir():
                        if item.is_dir() and "firefox" in item.name.lower():
                            firefox_found = True
                            break

                if firefox_found:
                    return True, "✓ Firefox браузер установлен"
                else:
                    return False, (
                        "❌ Firefox браузер не установлен для Playwright\n"
                        "Установите с помощью команды:\n"
                        "  playwright install firefox\n"
                        "Или установите все браузеры:\n"
                        "  playwright install"
                    )

            except subprocess.TimeoutExpired:
                return False, (
                    "❌ Превышено время ожидания проверки Firefox\n"
                    "Попробуйте установить вручную: playwright install firefox"
                )
            except Exception as e:
                return False, (
                    f"❌ Ошибка при проверке Firefox: {str(e)}\n"
                    "Попробуйте установить вручную: playwright install firefox"
                )

        except Exception as e:
            return False, f"❌ Ошибка при проверке Playwright: {str(e)}"

    @staticmethod
    def check_dotenv() -> Tuple[bool, str]:
        """
        Проверить наличие файла .env

        Returns:
            (success, message): результат проверки и сообщение
        """
        env_file = Path(".env")
        if not env_file.exists():
            return False, (
                "⚠️  Файл .env не найден\n"
                "Создайте файл .env в корне проекта и добавьте:\n"
                "  GROQ_API_KEY=your_api_key_here\n"
                "Получите ключ на: https://console.groq.com"
            )

        # Проверяем наличие GROQ_API_KEY в .env
        with open(env_file, 'r') as f:
            content = f.read()
            if "GROQ_API_KEY" not in content:
                return False, (
                    "⚠️  GROQ_API_KEY не найден в .env\n"
                    "Добавьте в файл .env:\n"
                    "  GROQ_API_KEY=your_api_key_here\n"
                    "Получите ключ на: https://console.groq.com"
                )

            # Проверяем что ключ не пустой
            for line in content.split('\n'):
                if line.startswith('GROQ_API_KEY'):
                    key = line.split('=', 1)[1].strip()
                    if not key or key == "your_api_key_here":
                        return False, (
                            "⚠️  GROQ_API_KEY пустой или не настроен\n"
                            "Замените значение в .env на ваш реальный API ключ\n"
                            "Получите ключ на: https://console.groq.com"
                        )

        return True, "✓ Файл .env настроен"

    @staticmethod
    def check_dependencies() -> Tuple[bool, str]:
        """
        Проверить основные зависимости

        Returns:
            (success, message): результат проверки и сообщение
        """
        missing_deps = []

        # Проверяем основные пакеты
        required_packages = {
            'openai': 'OpenAI SDK',
            'playwright': 'Playwright',
            'dotenv': 'python-dotenv'
        }

        for package, name in required_packages.items():
            try:
                __import__(package)
            except ImportError:
                missing_deps.append(name)

        if missing_deps:
            return False, (
                f"❌ Отсутствуют зависимости: {', '.join(missing_deps)}\n"
                "Установите с помощью: pip install -r requirements.txt"
            )

        return True, "✓ Все зависимости установлены"

    @classmethod
    def run_all_checks(cls, verbose: bool = True) -> Tuple[bool, list]:
        """
        Запустить все проверки системы

        Args:
            verbose: выводить детальную информацию

        Returns:
            (all_passed, messages): все ли проверки прошли и список сообщений
        """
        checks = [
            ("Python версия", cls.check_python_version),
            ("Зависимости", cls.check_dependencies),
            ("Playwright", cls.check_playwright_installation),
            ("Firefox браузер", cls.check_firefox_browser),
            ("Конфигурация .env", cls.check_dotenv),
        ]

        all_passed = True
        messages = []

        if verbose:
            print("=" * 70)
            print("🔍 ПРОВЕРКА СИСТЕМНЫХ ТРЕБОВАНИЙ")
            print("=" * 70)

        for check_name, check_func in checks:
            success, message = check_func()
            messages.append(message)

            if verbose:
                print(f"\n{check_name}:")
                print(f"  {message}")

            if not success:
                all_passed = False

        if verbose:
            print("\n" + "=" * 70)
            if all_passed:
                print("✅ ВСЕ ПРОВЕРКИ ПРОШЛИ УСПЕШНО")
            else:
                print("❌ ОБНАРУЖЕНЫ ПРОБЛЕМЫ")
                print("\nИсправьте указанные проблемы и запустите программу снова.")
            print("=" * 70 + "\n")

        return all_passed, messages


def run_system_check() -> bool:
    """
    Запустить проверку системы

    Returns:
        True если все проверки прошли, False иначе
    """
    all_passed, _ = SystemCheck.run_all_checks(verbose=True)
    return all_passed
