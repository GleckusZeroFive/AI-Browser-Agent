"""
Context Extractor - автоматическое извлечение критичной информации из диалога

Философия: LLM сам определяет что важно, мы только помогаем не забыть
"""
import json
import logging
from typing import Dict, Any, Optional
from openai import OpenAI


class ContextExtractor:
    """
    Извлекает важный контекст из разговора автоматически

    Контекст сохраняется между раундами диалога и используется
    только там где релевантен (не передается везде бездумно).
    """

    # Маппинг типов контекста к действиям где они важны
    CONTEXT_RELEVANCE = {
        "dietary_restrictions": ["click_by_text", "get_modal_text", "get_page_text", "scroll"],
        "people_count": ["click_by_text", "get_modal_text"],
        "budget": ["click_by_text", "get_page_text"],
        "location": ["navigate", "type_text"],
        "delivery_address": ["type_text", "click_by_text"],
        "delivery_time": ["click_by_text", "type_text"],
    }

    def __init__(self, llm_client: OpenAI):
        """
        Инициализация экстрактора

        Args:
            llm_client: OpenAI клиент для LLM запросов
        """
        self.llm = llm_client
        self.extracted_context: Dict[str, Any] = {}
        self.logger = logging.getLogger(__name__)

    async def extract_from_turn(self, user_msg: str, agent_response: str) -> None:
        """
        Извлекает критичную информацию из раунда диалога

        Примеры извлекаемой информации:
        - Аллергии/ограничения питания
        - Количество людей
        - Бюджет
        - Город доставки
        - Адрес доставки
        - Время доставки

        Args:
            user_msg: сообщение пользователя
            agent_response: ответ агента
        """
        # Спрашиваем LLM: есть ли важная информация?
        extraction_prompt = f"""Проанализируй диалог и извлеки ТОЛЬКО критичную информацию,
которую нужно помнить для выполнения задачи.

User: {user_msg}
Agent: {agent_response}

Верни JSON с полями (пустые если нет информации):
{{
  "dietary_restrictions": "аллергия на морепродукты",
  "people_count": 4,
  "budget": 2000,
  "location": "Красноярск",
  "delivery_address": "ул. Ленина, 10",
  "delivery_time": "18:00"
}}

ВАЖНО:
- Если ничего критичного - верни пустой объект {{}}.
- Не выдумывай информацию - только то что явно сказал пользователь.
- Для dietary_restrictions включай ВСЕ ограничения (аллергии, непереносимость, религиозные, веганство и т.д.)

Верни ТОЛЬКО JSON, без дополнительного текста."""

        try:
            # Используем OpenAI API
            response = self.llm.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",  # Быстрая модель для extraction
                messages=[{"role": "user", "content": extraction_prompt}],
                temperature=0.2,
                max_tokens=500,
            )

            response_text = response.choices[0].message.content
            self.logger.debug(f"Extraction response: {response_text}")

            # Парсим JSON
            extracted = self._parse_json_safely(response_text)

            if extracted:
                # Обновляем только непустые поля
                for key, value in extracted.items():
                    if value:
                        # Логируем извлечение
                        if key not in self.extracted_context:
                            self.logger.info(f"Извлечен новый контекст: {key} = {value}")
                        elif self.extracted_context[key] != value:
                            self.logger.info(f"Обновлен контекст: {key} = {value} (было: {self.extracted_context[key]})")

                        self.extracted_context[key] = value

        except Exception as e:
            # Не фейлим если extraction не удался - просто логируем
            self.logger.warning(f"Не удалось извлечь контекст: {e}")

    def _parse_json_safely(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Безопасный парсинг JSON из ответа LLM

        LLM может вернуть:
        - Чистый JSON: {"key": "value"}
        - JSON в markdown: ```json {"key": "value"} ```
        - JSON с текстом до/после

        Args:
            response: ответ от LLM

        Returns:
            Распарсенный dict или None при ошибке
        """
        # Убираем пробелы
        response = response.strip()

        # Если ответ в markdown - извлекаем JSON
        if "```" in response:
            # Ищем блок ```json ... ``` или ``` ... ```
            import re
            match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
            if match:
                response = match.group(1)

        # Если есть текст до/после JSON - пытаемся найти JSON
        if not response.startswith("{"):
            import re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                response = match.group(0)

        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            self.logger.warning(f"JSON parse error: {e}. Response: {response[:100]}")
            return None

    def get_context_for_action(self, action_type: str) -> str:
        """
        Возвращает только релевантный контекст для данного действия

        Не весь контекст важен для всех действий. Например:
        - dietary_restrictions важны для click_by_text (выбор блюда)
        - location важен для navigate (переход на сайт города)
        - budget не нужен для scroll (просто скроллим)

        Args:
            action_type: тип действия (navigate, click_by_text и т.д.)

        Returns:
            Отформатированная строка с релевантным контекстом
        """
        if not self.extracted_context:
            return ""

        relevant_items = []

        for context_key, context_value in self.extracted_context.items():
            # Проверяем релевантен ли этот контекст для действия
            if context_key in self.CONTEXT_RELEVANCE:
                relevant_actions = self.CONTEXT_RELEVANCE[context_key]

                if action_type in relevant_actions:
                    # Форматируем красиво
                    formatted = self._format_context_item(context_key, context_value)
                    if formatted:
                        relevant_items.append(formatted)

        if relevant_items:
            return "\n⚠️ ВАЖНАЯ ИНФОРМАЦИЯ:\n" + "\n".join(relevant_items)

        return ""

    def _format_context_item(self, key: str, value: Any) -> str:
        """
        Форматирует элемент контекста для вывода агенту

        Args:
            key: ключ контекста
            value: значение

        Returns:
            Отформатированная строка
        """
        formatters = {
            "dietary_restrictions": lambda v: f"🚨 ОГРАНИЧЕНИЯ: {v}",
            "people_count": lambda v: f"👥 Количество человек: {v}",
            "budget": lambda v: f"💰 Бюджет: до {v}₽",
            "location": lambda v: f"📍 Город: {v}",
            "delivery_address": lambda v: f"🏠 Адрес доставки: {v}",
            "delivery_time": lambda v: f"⏰ Время доставки: {v}",
        }

        formatter = formatters.get(key)
        if formatter:
            return formatter(value)

        return f"{key}: {value}"

    def get_all_context(self) -> Dict[str, Any]:
        """
        Получить весь извлеченный контекст

        Returns:
            Словарь с контекстом
        """
        return self.extracted_context.copy()

    def clear_context(self) -> None:
        """Очистить весь сохраненный контекст"""
        self.logger.info("Контекст очищен")
        self.extracted_context.clear()

    def remove_context_key(self, key: str) -> None:
        """
        Удалить конкретный ключ из контекста

        Args:
            key: ключ для удаления
        """
        if key in self.extracted_context:
            self.logger.info(f"Удален контекст: {key}")
            del self.extracted_context[key]

    def has_context(self) -> bool:
        """
        Проверить есть ли сохраненный контекст

        Returns:
            True если есть контекст
        """
        return bool(self.extracted_context)
