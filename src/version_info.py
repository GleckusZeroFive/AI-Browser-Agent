"""
Модуль для отображения информации о версиях библиотек
"""
import sys
from typing import Dict, Optional


def get_package_version(package_name: str) -> Optional[str]:
    """
    Получить версию установленного пакета

    Args:
        package_name: имя пакета

    Returns:
        версия пакета или None если не установлен
    """
    try:
        import importlib.metadata
        return importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        return None
    except Exception:
        return None


def get_all_versions() -> Dict[str, str]:
    """
    Получить версии всех основных зависимостей

    Returns:
        словарь {package_name: version}
    """
    packages = [
        ('python', f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"),
        ('openai', None),
        ('playwright', None),
        ('python-dotenv', None),
    ]

    versions = {}

    for package, predefined_version in packages:
        if predefined_version:
            versions[package] = predefined_version
        else:
            version = get_package_version(package)
            if version:
                versions[package] = version

    return versions


def print_version_info(verbose: bool = False):
    """
    Вывести информацию о версиях библиотек

    Args:
        verbose: выводить детальную информацию
    """
    print("\n📦 ВЕРСИИ БИБЛИОТЕК:")
    print("-" * 50)

    versions = get_all_versions()

    # Основные зависимости
    main_deps = {
        'python': 'Python',
        'openai': 'OpenAI SDK',
        'playwright': 'Playwright',
        'python-dotenv': 'python-dotenv'
    }

    for package, display_name in main_deps.items():
        version = versions.get(package)
        if version:
            print(f"  {display_name:20} v{version}")
        else:
            print(f"  {display_name:20} не установлен")

    if verbose:
        print("\n📌 Дополнительная информация:")
        print(f"  Python путь:        {sys.executable}")
        print(f"  Платформа:          {sys.platform}")

    print("-" * 50 + "\n")


def get_version_string() -> str:
    """
    Получить строку с версиями для логирования

    Returns:
        строка с версиями всех пакетов
    """
    versions = get_all_versions()
    parts = []

    for package, version in versions.items():
        if version:
            parts.append(f"{package}={version}")

    return ", ".join(parts)
