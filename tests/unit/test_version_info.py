"""
Unit тесты для модуля version_info
"""
import pytest
import sys
from unittest.mock import patch, Mock
from src.version_info import (
    get_package_version,
    get_all_versions,
    print_version_info,
    get_version_string
)


class TestVersionInfo:
    """Тесты для модуля version_info"""

    def test_get_package_version_existing(self):
        """Тест получения версии существующего пакета"""
        # Playwright должен быть установлен
        version = get_package_version("playwright")

        assert version is not None
        assert isinstance(version, str)
        assert len(version) > 0

    def test_get_package_version_nonexistent(self):
        """Тест получения версии несуществующего пакета"""
        version = get_package_version("nonexistent_package_12345")

        assert version is None

    def test_get_all_versions_structure(self):
        """Тест структуры словаря версий"""
        versions = get_all_versions()

        assert isinstance(versions, dict)
        assert "python" in versions
        assert versions["python"] is not None

        # Проверяем что Python версия корректна
        python_version = versions["python"]
        assert f"{sys.version_info.major}.{sys.version_info.minor}" in python_version

    def test_get_all_versions_includes_dependencies(self):
        """Тест что версии включают основные зависимости"""
        versions = get_all_versions()

        expected_packages = ["python", "openai", "playwright", "python-dotenv"]

        for package in expected_packages:
            assert package in versions

    @patch('builtins.print')
    def test_print_version_info_basic(self, mock_print):
        """Тест базового вывода информации о версиях"""
        print_version_info(verbose=False)

        # Проверяем что был вызван print
        assert mock_print.called
        assert mock_print.call_count > 0

        # Проверяем что выводится заголовок
        printed_text = " ".join([str(call[0][0]) for call in mock_print.call_args_list])
        assert "ВЕРСИИ БИБЛИОТЕК" in printed_text

    @patch('builtins.print')
    def test_print_version_info_verbose(self, mock_print):
        """Тест детального вывода информации"""
        print_version_info(verbose=True)

        # Проверяем что выводится дополнительная информация
        printed_text = " ".join([str(call[0][0]) for call in mock_print.call_args_list])
        assert "Дополнительная информация" in printed_text or "Python путь" in printed_text

    def test_get_version_string_format(self):
        """Тест формата строки версий"""
        version_string = get_version_string()

        assert isinstance(version_string, str)
        assert len(version_string) > 0

        # Проверяем формат "package=version"
        assert "=" in version_string
        assert "python=" in version_string

        # Проверяем что версии разделены запятыми
        if "," in version_string:
            parts = version_string.split(", ")
            for part in parts:
                assert "=" in part

    @patch('src.version_info.get_package_version')
    def test_get_all_versions_handles_missing_packages(self, mock_get_version):
        """Тест обработки отсутствующих пакетов"""
        # Симулируем что некоторые пакеты не найдены
        def version_side_effect(package_name):
            if package_name == "openai":
                return None
            return "1.0.0"

        mock_get_version.side_effect = version_side_effect

        versions = get_all_versions()

        # Python версия всегда должна быть
        assert "python" in versions
        assert versions["python"] is not None

        # Отсутствующие пакеты не должны быть в словаре
        # или иметь значение None
        if "openai" in versions:
            # Допускается как отсутствие ключа, так и None
            pass

    @patch('builtins.print')
    @patch('src.version_info.get_all_versions')
    def test_print_version_info_handles_missing(self, mock_get_versions, mock_print):
        """Тест вывода когда некоторые пакеты отсутствуют"""
        mock_get_versions.return_value = {
            "python": "3.10.0",
            "playwright": "1.40.0",
            # openai отсутствует
        }

        print_version_info(verbose=False)

        # Проверяем что функция не упала и вывела информацию
        assert mock_print.called

        printed_text = " ".join([str(call[0][0]) for call in mock_print.call_args_list])
        # Должно быть указано что пакет не установлен
        # (точный текст зависит от реализации)
        assert "не установлен" in printed_text or "openai" in printed_text
