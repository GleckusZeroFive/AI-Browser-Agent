"""
Unit тесты для модуля system_check
"""
import pytest
import sys
from unittest.mock import patch, Mock
from src.system_check import SystemCheck


class TestSystemCheck:
    """Тесты для SystemCheck"""

    def test_check_python_version_success(self):
        """Тест успешной проверки версии Python"""
        success, message = SystemCheck.check_python_version()

        # Python 3.10+ требуется
        if sys.version_info >= (3, 10):
            assert success is True
            assert "Python" in message
            assert "✓" in message
        else:
            assert success is False
            assert "Требуется Python 3.10" in message

    @patch('sys.version_info')
    def test_check_python_version_old(self, mock_version):
        """Тест проверки старой версии Python"""
        mock_version.major = 3
        mock_version.minor = 9
        mock_version.micro = 0

        success, message = SystemCheck.check_python_version()

        assert success is False
        assert "Требуется Python 3.10" in message
        assert "3.9" in message

    def test_check_playwright_installation_success(self):
        """Тест успешной проверки Playwright"""
        success, message = SystemCheck.check_playwright_installation()

        # Playwright должен быть установлен в тестовом окружении
        assert success is True
        assert "Playwright" in message
        assert "✓" in message

    @patch('src.system_check.__import__')
    def test_check_playwright_installation_missing(self, mock_import):
        """Тест проверки отсутствующего Playwright"""
        mock_import.side_effect = ImportError("No module named 'playwright'")

        success, message = SystemCheck.check_playwright_installation()

        assert success is False
        assert "не установлен" in message
        assert "pip install" in message

    def test_check_dependencies_success(self):
        """Тест успешной проверки зависимостей"""
        success, message = SystemCheck.check_dependencies()

        # В тестовом окружении все зависимости должны быть
        assert success is True
        assert "зависимости установлены" in message

    @patch('src.system_check.__import__')
    def test_check_dependencies_missing(self, mock_import):
        """Тест проверки отсутствующих зависимостей"""
        def import_side_effect(name):
            if name == 'openai':
                raise ImportError("No module named 'openai'")
            return Mock()

        mock_import.side_effect = import_side_effect

        success, message = SystemCheck.check_dependencies()

        assert success is False
        assert "Отсутствуют зависимости" in message

    def test_check_dotenv_missing(self, tmp_path, monkeypatch):
        """Тест проверки отсутствующего .env файла"""
        # Переключаемся в пустую временную директорию
        monkeypatch.chdir(tmp_path)

        success, message = SystemCheck.check_dotenv()

        assert success is False
        assert ".env не найден" in message
        assert "GROQ_API_KEY" in message

    def test_check_dotenv_missing_key(self, tmp_path, monkeypatch):
        """Тест проверки .env без GROQ_API_KEY"""
        monkeypatch.chdir(tmp_path)

        # Создаем .env без GROQ_API_KEY
        env_file = tmp_path / ".env"
        env_file.write_text("SOME_OTHER_KEY=value\n")

        success, message = SystemCheck.check_dotenv()

        assert success is False
        assert "GROQ_API_KEY не найден" in message

    def test_check_dotenv_empty_key(self, tmp_path, monkeypatch):
        """Тест проверки .env с пустым GROQ_API_KEY"""
        monkeypatch.chdir(tmp_path)

        env_file = tmp_path / ".env"
        env_file.write_text("GROQ_API_KEY=\n")

        success, message = SystemCheck.check_dotenv()

        assert success is False
        assert "пустой" in message

    def test_check_dotenv_placeholder_key(self, tmp_path, monkeypatch):
        """Тест проверки .env с placeholder ключом"""
        monkeypatch.chdir(tmp_path)

        env_file = tmp_path / ".env"
        env_file.write_text("GROQ_API_KEY=your_api_key_here\n")

        success, message = SystemCheck.check_dotenv()

        assert success is False
        assert "не настроен" in message

    def test_check_dotenv_valid_key(self, tmp_path, monkeypatch):
        """Тест проверки .env с валидным ключом"""
        monkeypatch.chdir(tmp_path)

        env_file = tmp_path / ".env"
        env_file.write_text("GROQ_API_KEY=gsk_123456789abcdef\n")

        success, message = SystemCheck.check_dotenv()

        assert success is True
        assert "настроен" in message

    @patch.object(SystemCheck, 'check_python_version')
    @patch.object(SystemCheck, 'check_dependencies')
    @patch.object(SystemCheck, 'check_playwright_installation')
    @patch.object(SystemCheck, 'check_firefox_browser')
    @patch.object(SystemCheck, 'check_dotenv')
    def test_run_all_checks_success(
        self,
        mock_dotenv,
        mock_firefox,
        mock_playwright,
        mock_deps,
        mock_python
    ):
        """Тест успешного прохождения всех проверок"""
        # Все проверки возвращают успех
        mock_python.return_value = (True, "✓ Python 3.10")
        mock_deps.return_value = (True, "✓ Dependencies")
        mock_playwright.return_value = (True, "✓ Playwright")
        mock_firefox.return_value = (True, "✓ Firefox")
        mock_dotenv.return_value = (True, "✓ .env configured")

        all_passed, messages = SystemCheck.run_all_checks(verbose=False)

        assert all_passed is True
        assert len(messages) == 5

    @patch.object(SystemCheck, 'check_python_version')
    @patch.object(SystemCheck, 'check_dependencies')
    def test_run_all_checks_failure(self, mock_deps, mock_python):
        """Тест провала некоторых проверок"""
        mock_python.return_value = (False, "❌ Old Python")
        mock_deps.return_value = (True, "✓ Dependencies")

        all_passed, messages = SystemCheck.run_all_checks(verbose=False)

        assert all_passed is False
