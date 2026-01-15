"""
Unit tests for ContextExtractor
"""
import pytest
from unittest.mock import Mock, MagicMock
from src.agent.context_extractor import ContextExtractor


class TestContextExtractor:
    """Тесты для ContextExtractor"""

    @pytest.fixture
    def mock_llm_client(self):
        """Mock OpenAI client"""
        client = Mock()
        # Мокаем структуру OpenAI API
        client.chat.completions.create = MagicMock()
        return client

    @pytest.fixture
    def extractor(self, mock_llm_client):
        """Создать экстрактор с моковым клиентом"""
        return ContextExtractor(mock_llm_client)

    def test_initialization(self, extractor, mock_llm_client):
        """Тест инициализации"""
        assert extractor.llm == mock_llm_client
        assert extractor.extracted_context == {}
        assert not extractor.has_context()

    def test_parse_json_safely_valid(self, extractor):
        """Тест парсинга валидного JSON"""
        json_str = '{"dietary_restrictions": "без мяса", "people_count": 2}'
        result = extractor._parse_json_safely(json_str)

        assert result is not None
        assert result["dietary_restrictions"] == "без мяса"
        assert result["people_count"] == 2

    def test_parse_json_safely_markdown(self, extractor):
        """Тест парсинга JSON в markdown блоке"""
        json_str = '```json\n{"dietary_restrictions": "без орехов"}\n```'
        result = extractor._parse_json_safely(json_str)

        assert result is not None
        assert result["dietary_restrictions"] == "без орехов"

    def test_parse_json_safely_with_text(self, extractor):
        """Тест парсинга JSON с текстом до/после"""
        json_str = 'Вот результат: {"budget": 1000} - надеюсь помогло'
        result = extractor._parse_json_safely(json_str)

        assert result is not None
        assert result["budget"] == 1000

    def test_parse_json_safely_invalid(self, extractor):
        """Тест парсинга невалидного JSON"""
        json_str = 'Это просто текст без JSON'
        result = extractor._parse_json_safely(json_str)

        assert result is None

    def test_get_context_for_action_dietary_restrictions(self, extractor):
        """Тест получения контекста для действия с dietary restrictions"""
        # Добавляем контекст
        extractor.extracted_context["dietary_restrictions"] = "аллергия на морепродукты"

        # Для click_by_text dietary_restrictions релевантны
        context = extractor.get_context_for_action("click_by_text")
        assert "🚨 ОГРАНИЧЕНИЯ" in context
        assert "аллергия на морепродукты" in context

    def test_get_context_for_action_irrelevant(self, extractor):
        """Тест что контекст не возвращается для нерелевантных действий"""
        # Добавляем budget
        extractor.extracted_context["budget"] = 2000

        # Для scroll budget не релевантен
        context = extractor.get_context_for_action("scroll")
        assert context == ""

    def test_get_context_for_action_multiple_items(self, extractor):
        """Тест получения нескольких релевантных элементов контекста"""
        extractor.extracted_context["dietary_restrictions"] = "без лактозы"
        extractor.extracted_context["people_count"] = 4

        # Оба релевантны для click_by_text
        context = extractor.get_context_for_action("click_by_text")
        assert "ОГРАНИЧЕНИЯ" in context
        assert "без лактозы" in context
        assert "Количество человек: 4" in context

    def test_format_context_item(self, extractor):
        """Тест форматирования элементов контекста"""
        assert "🚨 ОГРАНИЧЕНИЯ" in extractor._format_context_item(
            "dietary_restrictions", "аллергия"
        )
        assert "👥 Количество человек: 3" == extractor._format_context_item(
            "people_count", 3
        )
        assert "💰 Бюджет: до 1500₽" == extractor._format_context_item(
            "budget", 1500
        )
        assert "📍 Город: Москва" == extractor._format_context_item(
            "location", "Москва"
        )

    def test_get_all_context(self, extractor):
        """Тест получения всего контекста"""
        extractor.extracted_context["location"] = "Красноярск"
        extractor.extracted_context["budget"] = 3000

        all_context = extractor.get_all_context()

        assert all_context["location"] == "Красноярск"
        assert all_context["budget"] == 3000
        # Проверяем что это копия, не оригинал
        assert all_context is not extractor.extracted_context

    def test_clear_context(self, extractor):
        """Тест очистки контекста"""
        extractor.extracted_context["location"] = "Москва"
        assert extractor.has_context()

        extractor.clear_context()

        assert not extractor.has_context()
        assert extractor.extracted_context == {}

    def test_remove_context_key(self, extractor):
        """Тест удаления конкретного ключа"""
        extractor.extracted_context["location"] = "Москва"
        extractor.extracted_context["budget"] = 1000

        extractor.remove_context_key("location")

        assert "location" not in extractor.extracted_context
        assert "budget" in extractor.extracted_context

    def test_has_context(self, extractor):
        """Тест проверки наличия контекста"""
        assert not extractor.has_context()

        extractor.extracted_context["location"] = "Москва"
        assert extractor.has_context()

    @pytest.mark.asyncio
    async def test_extract_from_turn_success(self, extractor, mock_llm_client):
        """Тест успешного извлечения контекста"""
        # Мокаем ответ API
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"dietary_restrictions": "без глютена"}'
        mock_llm_client.chat.completions.create.return_value = mock_response

        await extractor.extract_from_turn(
            "Хочу заказать пиццу, но у меня непереносимость глютена",
            "Понял, буду искать безглютеновую пиццу"
        )

        # Проверяем что контекст извлечен
        assert "dietary_restrictions" in extractor.extracted_context
        assert extractor.extracted_context["dietary_restrictions"] == "без глютена"

    @pytest.mark.asyncio
    async def test_extract_from_turn_empty_response(self, extractor, mock_llm_client):
        """Тест извлечения когда LLM не нашел контекста"""
        # Мокаем пустой ответ
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{}'
        mock_llm_client.chat.completions.create.return_value = mock_response

        await extractor.extract_from_turn(
            "Как дела?",
            "Хорошо, готов помочь!"
        )

        # Контекст не должен быть извлечен
        assert not extractor.has_context()

    @pytest.mark.asyncio
    async def test_extract_from_turn_api_error(self, extractor, mock_llm_client):
        """Тест обработки ошибки API при извлечении"""
        # Мокаем ошибку API
        mock_llm_client.chat.completions.create.side_effect = Exception("API Error")

        # Не должно упасть, просто залогируется
        await extractor.extract_from_turn(
            "Заказ пиццы",
            "Хорошо"
        )

        # Контекст не извлечен но программа не упала
        assert not extractor.has_context()

    @pytest.mark.asyncio
    async def test_extract_from_turn_updates_existing(self, extractor, mock_llm_client):
        """Тест обновления существующего контекста"""
        # Устанавливаем начальный контекст
        extractor.extracted_context["people_count"] = 2

        # Мокаем ответ с обновлением
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"people_count": 4}'
        mock_llm_client.chat.completions.create.return_value = mock_response

        await extractor.extract_from_turn(
            "На самом деле нас будет 4 человека",
            "Хорошо, учту что вас 4"
        )

        # Проверяем что контекст обновлен
        assert extractor.extracted_context["people_count"] == 4
