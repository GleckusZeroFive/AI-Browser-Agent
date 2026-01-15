import os
from typing import Optional
from enum import Enum
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

class ModelType(Enum):
    """Типы моделей для разных задач"""
    FAST = "fast"           # Быстрые простые запросы (диалог, уточнения)
    SMART = "smart"         # Сложные запросы (планирование, анализ)
    REASONING = "reasoning" # Рассуждения и принятие решений

class Config:
    """Конфигурация проекта"""

    # API ключи (загружаются из переменных окружения)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

    # Настройки Groq
    GROQ_BASE_URL: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")

    # Модели для разных типов запросов
    MODELS = {
        ModelType.FAST: "meta-llama/llama-4-scout-17b-16e-instruct",  # Быстрая, меньше rate limit
        ModelType.SMART: "llama-3.3-70b-versatile",                   # Умная, но больше rate limit
        ModelType.REASONING: "meta-llama/llama-4-maverick-17b-128e-instruct",  # Баланс
    }

    # Модель по умолчанию
    DEFAULT_MODEL: str = MODELS[ModelType.FAST]

    # Fallback модели при rate limit (в порядке приоритета)
    FALLBACK_MODELS = [
        "meta-llama/llama-4-scout-17b-16e-instruct",
        "meta-llama/llama-4-maverick-17b-128e-instruct",
        "llama-3.1-8b-instant",
    ]

    MAX_TOKENS: int = 2000
    TEMPERATURE: float = 0.7

    # Настройки браузера
    BROWSER_HEADLESS: bool = False
    SCREENSHOT_DIR: str = "screenshots"
    LOGS_DIR: str = "logs"

    # Настройки таймаутов и keepalive
    USER_INPUT_TIMEOUT: int = 300  # Таймаут ожидания ввода (секунды) - 5 минут
    USER_INPUT_GRACE_PERIOD: int = 60  # Дополнительное время после предупреждения (секунды)
    KEEPALIVE_INTERVAL: int = 60  # Интервал проверки браузера (секунды)
    BROWSER_CHECK_ENABLED: bool = True  # Включить keepalive проверки браузера

    # Настройки rate limit
    MIN_REQUEST_INTERVAL: float = 1.0  # Минимальный интервал между запросами (секунды)
    RATE_LIMIT_RETRY_DELAY: float = 5.0  # Задержка при rate limit (секунды)

    @classmethod
    def get_api_key(cls) -> str:
        """Получить API ключ Groq"""
        if not cls.GROQ_API_KEY:
            raise ValueError(
                "GROQ_API_KEY не найден!\n"
                "Пожалуйста, создайте файл .env в корне проекта и добавьте:\n"
                "GROQ_API_KEY=your_api_key_here\n"
                "Или используйте .env.example как шаблон."
            )
        return cls.GROQ_API_KEY

    @classmethod
    def get_base_url(cls) -> str:
        """Получить базовый URL Groq"""
        return cls.GROQ_BASE_URL

    @classmethod
    def get_model(cls, model_type: ModelType = None) -> str:
        """Получить модель по типу"""
        if model_type is None:
            return cls.DEFAULT_MODEL
        return cls.MODELS.get(model_type, cls.DEFAULT_MODEL)
