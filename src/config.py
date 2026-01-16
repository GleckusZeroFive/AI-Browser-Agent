import os
from typing import Optional, List
from enum import Enum
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

class ModelType(Enum):
    """Типы моделей для разных задач"""
    FAST = "fast"           # Быстрые простые запросы (диалог, уточнения)
    SMART = "smart"         # Сложные запросы (планирование, анализ)
    REASONING = "reasoning" # Рассуждения и принятие решений
    VISION = "vision"       # Анализ скриншотов страниц

class Config:
    """Конфигурация проекта"""

    # API ключи (загружаются из переменных окружения)
    # Поддержка нескольких ключей для обхода дневных лимитов
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_API_KEYS: List[str] = []  # Список всех ключей для ротации
    _current_key_index: int = 0  # Текущий индекс ключа

    @classmethod
    def _init_api_keys(cls):
        """Инициализация списка API ключей"""
        if cls.GROQ_API_KEYS:
            return  # Уже инициализировано

        keys = []

        # Основной ключ из GROQ_API_KEY
        if cls.GROQ_API_KEY:
            keys.append(cls.GROQ_API_KEY)

        # Дополнительные ключи из GROQ_API_KEY_2, GROQ_API_KEY_3, ...
        for i in range(2, 10):
            key = os.getenv(f"GROQ_API_KEY_{i}", "")
            if key:
                keys.append(key)

        cls.GROQ_API_KEYS = keys

    @classmethod
    def get_current_api_key(cls) -> str:
        """Получить текущий API ключ"""
        cls._init_api_keys()
        if not cls.GROQ_API_KEYS:
            raise ValueError(
                "\n❌ GROQ_API_KEY не найден или не настроен!\n\n"
                "Для работы агента необходим API ключ Groq.\n\n"
                "Шаги для настройки:\n"
                "1. Зарегистрируйтесь на https://console.groq.com\n"
                "2. Создайте новый API ключ в разделе 'API Keys'\n"
                "3. Создайте файл .env в корне проекта\n"
                "4. Добавьте в файл .env строку:\n"
                "   GROQ_API_KEY=ваш_ключ_здесь\n\n"
                "Для нескольких ключей (обход дневных лимитов):\n"
                "   GROQ_API_KEY=ключ1\n"
                "   GROQ_API_KEY_2=ключ2\n"
                "   GROQ_API_KEY_3=ключ3\n"
            )
        return cls.GROQ_API_KEYS[cls._current_key_index]

    @classmethod
    def rotate_api_key(cls) -> bool:
        """
        Переключиться на следующий API ключ.
        Возвращает True если удалось переключиться, False если ключи закончились.
        """
        cls._init_api_keys()
        if len(cls.GROQ_API_KEYS) <= 1:
            return False

        cls._current_key_index = (cls._current_key_index + 1) % len(cls.GROQ_API_KEYS)
        return True

    @classmethod
    def get_api_keys_count(cls) -> int:
        """Получить количество доступных API ключей"""
        cls._init_api_keys()
        return len(cls.GROQ_API_KEYS)

    @classmethod
    def get_current_key_index(cls) -> int:
        """Получить индекс текущего ключа (для логирования)"""
        return cls._current_key_index + 1  # 1-based для пользователя

    # Настройки Groq
    GROQ_BASE_URL: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")

    # Модели для разных типов запросов
    MODELS = {
        ModelType.FAST: "meta-llama/llama-4-scout-17b-16e-instruct",  # Быстрая, меньше rate limit
        ModelType.SMART: "llama-3.3-70b-versatile",                   # Умная, но больше rate limit
        ModelType.REASONING: "meta-llama/llama-4-maverick-17b-128e-instruct",  # Баланс
        ModelType.VISION: "meta-llama/llama-4-scout-17b-16e-instruct",  # Multimodal (vision + text)
    }

    # Модель по умолчанию
    DEFAULT_MODEL: str = MODELS[ModelType.FAST]

    # Fallback модели при rate limit (в порядке приоритета)
    # ВАЖНО: Модели отсортированы по лимиту токенов (от большего к меньшему)
    # Это критично для работы со специализированными агентами (большие промпты)
    FALLBACK_MODELS = [
        "llama-3.1-8b-instant",  # 30,000 TPM - максимальный лимит
        "meta-llama/llama-4-scout-17b-16e-instruct",  # 14,400 TPM
        "meta-llama/llama-4-maverick-17b-128e-instruct",  # 6,000 TPM - минимальный
    ]

    # Лимиты токенов для каждой модели (tokens per minute)
    MODEL_TOKEN_LIMITS = {
        "meta-llama/llama-4-scout-17b-16e-instruct": 14400,
        "meta-llama/llama-4-maverick-17b-128e-instruct": 6000,
        "llama-3.3-70b-versatile": 6000,
        "llama-3.1-8b-instant": 30000,
    }

    MAX_TOKENS: int = 2000
    TEMPERATURE: float = 0.7

    # Управление контекстом разговора
    MAX_CONTEXT_MESSAGES: int = 20  # Максимальное количество сообщений в истории
    CONTEXT_TRIM_TO: int = 12  # До скольких сообщений сокращать при превышении
    SAFE_TOKEN_MARGIN: float = 0.7  # Использовать 70% от лимита модели для безопасности

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

    # Настройки обработки капчи
    CAPTCHA_AUTO_HANDLE: bool = True  # Автоматически обрабатывать капчи
    CAPTCHA_MANUAL_TIMEOUT: int = 300  # Таймаут ручного решения (секунды)
    CAPTCHA_CHECK_INTERVAL: int = 2  # Интервал проверки решения (секунды)

    # Опционально: Сервис автоматического решения (требует API ключ)
    CAPTCHA_SOLVER_SERVICE: Optional[str] = os.getenv("CAPTCHA_SOLVER_SERVICE")  # "2captcha" или "anticaptcha"
    CAPTCHA_SOLVER_API_KEY: Optional[str] = os.getenv("CAPTCHA_SOLVER_API_KEY")

    # Режим отладки (показывает статистику токенов)
    DEBUG_MODE: bool = os.getenv("DEBUG_MODE", "false").lower() == "true"

    # Настройки Vision (использовать скриншоты вместо текста)
    USE_VISION: bool = os.getenv("USE_VISION", "true").lower() == "true"
    VISION_MODEL: str = "meta-llama/llama-4-scout-17b-16e-instruct"  # Multimodal model
    SCREENSHOT_MAX_SIZE: int = 1920  # Максимальная ширина скриншота в пикселях

    @classmethod
    def get_api_key(cls) -> str:
        """Получить API ключ Groq (для обратной совместимости)"""
        return cls.get_current_api_key()

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
