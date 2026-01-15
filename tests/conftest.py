"""
Общие фикстуры для pytest тестов
"""
import pytest
import asyncio
import os
from pathlib import Path
from unittest.mock import Mock, AsyncMock
from src.config import Config
from src.tools.browser_tools import BrowserTools
from src.agent.ai_agent import AIAgent


@pytest.fixture(scope="session")
def event_loop():
    """
    Создать event loop для async тестов
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_config(monkeypatch):
    """
    Мок конфигурации для тестов
    """
    monkeypatch.setenv("GROQ_API_KEY", "test_api_key_123")
    monkeypatch.setattr(Config, "GROQ_API_KEY", "test_api_key_123")
    monkeypatch.setattr(Config, "BROWSER_HEADLESS", True)
    return Config


@pytest.fixture
def mock_browser_tools():
    """
    Мок BrowserTools для тестирования без реального браузера
    """
    mock_tools = Mock(spec=BrowserTools)
    mock_tools.start_browser = AsyncMock(return_value={
        "status": "success",
        "message": "Браузер запущен"
    })
    mock_tools.navigate = AsyncMock(return_value={
        "status": "success",
        "message": "Перешли на URL",
        "url": "https://example.com",
        "title": "Example Domain"
    })
    mock_tools.get_page_text = AsyncMock(return_value={
        "status": "success",
        "text": "Test page content",
        "full_length": 100
    })
    mock_tools.click_by_text = AsyncMock(return_value={
        "status": "success",
        "message": "Кликнули по тексту"
    })
    mock_tools.close_browser = AsyncMock(return_value={
        "status": "success",
        "message": "Браузер закрыт"
    })
    return mock_tools


@pytest.fixture
def mock_ai_agent(mock_config):
    """
    Мок AIAgent для тестирования без реальных API запросов
    """
    mock_agent = Mock(spec=AIAgent)
    mock_agent.chat = Mock(return_value="Test response from AI")
    mock_agent.parse_action = Mock(return_value=None)
    mock_agent.add_system_prompt = Mock()
    mock_agent.conversation_history = []
    return mock_agent


@pytest.fixture
async def real_browser_tools():
    """
    Реальный BrowserTools для интеграционных тестов
    Используйте с маркером @pytest.mark.browser
    """
    tools = BrowserTools()
    await tools.start_browser(headless=True)
    yield tools
    await tools.close_browser()


@pytest.fixture
def temp_env_file(tmp_path, monkeypatch):
    """
    Создать временный .env файл для тестов
    """
    env_file = tmp_path / ".env"
    env_file.write_text("GROQ_API_KEY=test_key_123\n")

    # Изменить рабочую директорию на временную
    monkeypatch.chdir(tmp_path)

    return env_file


@pytest.fixture
def sample_page_html():
    """
    Пример HTML страницы для тестов
    """
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Page</title>
    </head>
    <body>
        <h1>Welcome to Test Page</h1>
        <button id="test-button">Click Me</button>
        <input id="test-input" type="text" placeholder="Enter text">
        <div class="content">
            <p>This is test content</p>
            <a href="/page2">Link to Page 2</a>
        </div>
    </body>
    </html>
    """


@pytest.fixture
def sample_action():
    """
    Пример действия для тестов
    """
    return {
        "action": "navigate",
        "params": {
            "url": "https://example.com"
        },
        "reasoning": "Открываю тестовую страницу"
    }


@pytest.fixture(autouse=True)
def cleanup_logs(request):
    """
    Очистка логов после тестов (опционально)
    """
    yield

    # Очистка только если тест упал
    if request.node.rep_call.failed:
        logs_dir = Path("logs")
        if logs_dir.exists():
            for log_file in logs_dir.glob("*.log"):
                # Можно добавить логику копирования логов в отчет
                pass


@pytest.fixture
def skip_if_no_api_key():
    """
    Пропустить тест если нет API ключа
    """
    if not os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API_KEY") == "test_api_key_123":
        pytest.skip("GROQ_API_KEY не настроен для интеграционных тестов")


# Хуки для pytest
def pytest_configure(config):
    """
    Конфигурация pytest при запуске
    """
    # Создать директории для тестов
    Path("logs").mkdir(exist_ok=True)
    Path("screenshots").mkdir(exist_ok=True)


def pytest_collection_modifyitems(config, items):
    """
    Изменить собранные тесты перед запуском
    """
    # Добавить маркер slow для браузерных тестов
    for item in items:
        if "browser" in item.keywords:
            item.add_marker(pytest.mark.slow)

        # Добавить маркер integration для тестов в папке integration/
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
