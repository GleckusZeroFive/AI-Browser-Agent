"""
Интеллектуальная компрессия контекста разговора
"""
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum


class MessageType(Enum):
    """Типы сообщений для классификации"""
    SYSTEM = "system"           # Системный промпт
    USER_QUESTION = "user_question"  # Вопрос от пользователя
    USER_ANSWER = "user_answer"      # Ответ пользователя на вопрос агента
    AGENT_ACTION = "agent_action"    # Действие агента (JSON)
    AGENT_QUESTION = "agent_question"  # Вопрос агента к пользователю
    PAGE_CONTEXT = "page_context"    # Контекст страницы (большой текст)
    ACTION_RESULT = "action_result"  # Результат действия


@dataclass
class MessageImportance:
    """Важность сообщения"""
    score: float  # 0.0 - 1.0
    reason: str


class ContextCompressor:
    """Умная компрессия контекста с сохранением важной информации"""

    # Ключевые слова для определения важности
    IMPORTANT_KEYWORDS = {
        'город', 'адрес', 'аллергия', 'бюджет', 'предпочтение',
        'нельзя', 'можно', 'нравится', 'не нравится',
        'location', 'address', 'allergy', 'budget', 'preference',
        'важно', 'критично', 'обязательно', 'запомни'
    }

    # Паттерны для определения типа сообщения
    ACTION_PATTERN = re.compile(r'\{"action":\s*"[^"]+",\s*"params":', re.IGNORECASE)
    PAGE_CONTEXT_PATTERN = re.compile(r'Контекст:|get_page_text\(\):|Текст страницы:', re.IGNORECASE)

    def __init__(self):
        self.compression_stats = {
            'original_count': 0,
            'compressed_count': 0,
            'tokens_saved': 0
        }

    def _estimate_tokens(self, text: str) -> int:
        """
        Оценка количества токенов

        Args:
            text: Текст для оценки

        Returns:
            Примерное количество токенов
        """
        if not text:
            return 0

        cyrillic_count = sum(1 for c in text if '\u0400' <= c <= '\u04FF')
        total_chars = len(text)
        latin_count = total_chars - cyrillic_count

        estimated_tokens = (cyrillic_count / 2.5) + (latin_count / 4.0)
        return int(estimated_tokens)

    def _classify_message(self, message: Dict[str, str]) -> MessageType:
        """
        Классифицировать сообщение по типу

        Args:
            message: Сообщение из conversation_history

        Returns:
            Тип сообщения
        """
        role = message.get("role", "")
        content = message.get("content", "")

        if role == "system":
            return MessageType.SYSTEM

        if role == "user":
            # Короткий ответ на вопрос агента
            if len(content) < 100 and not self.PAGE_CONTEXT_PATTERN.search(content):
                return MessageType.USER_ANSWER
            return MessageType.USER_QUESTION

        if role == "assistant":
            # JSON-действие
            if self.ACTION_PATTERN.search(content):
                return MessageType.AGENT_ACTION
            # Вопрос пользователю (обычно заканчивается ?)
            if content.strip().endswith('?'):
                return MessageType.AGENT_QUESTION
            # Результат действия
            return MessageType.ACTION_RESULT

        return MessageType.ACTION_RESULT

    def _calculate_importance(
        self,
        message: Dict[str, str],
        msg_type: MessageType,
        position_from_end: int = 999
    ) -> MessageImportance:
        """
        Вычислить важность сообщения

        Args:
            message: Сообщение
            msg_type: Тип сообщения
            position_from_end: Позиция сообщения с конца (0 = последнее)

        Returns:
            Оценка важности
        """
        content = message.get("content", "").lower()
        score = 0.0
        reasons = []

        # Системный промпт - всегда критичен
        if msg_type == MessageType.SYSTEM:
            return MessageImportance(1.0, "системный промпт")

        # НОВОЕ: Недавность - очень важный фактор!
        # Последние 5 сообщений получают бонус
        if position_from_end < 5:
            recency_bonus = (5 - position_from_end) * 0.15  # 0.75, 0.60, 0.45, 0.30, 0.15
            score += recency_bonus
            reasons.append(f"недавнее (#{position_from_end+1} с конца)")

        # Проверяем ключевые слова
        keyword_matches = sum(1 for kw in self.IMPORTANT_KEYWORDS if kw in content)
        if keyword_matches > 0:
            score += min(keyword_matches * 0.2, 0.6)
            reasons.append(f"ключевые слова ({keyword_matches})")

        # Вопросы и ответы пользователя важнее технических деталей
        if msg_type in (MessageType.USER_QUESTION, MessageType.USER_ANSWER):
            score += 0.3
            reasons.append("взаимодействие с пользователем")

        # Вопросы агента важны (помогают восстановить контекст)
        if msg_type == MessageType.AGENT_QUESTION:
            score += 0.4
            reasons.append("вопрос агента")

        # Контекст страницы обычно менее важен (устаревает быстро)
        if msg_type == MessageType.PAGE_CONTEXT or len(content) > 1000:
            score -= 0.3
            reasons.append("большой/технический контекст")

        # JSON-действия средней важности (показывают что делал агент)
        if msg_type == MessageType.AGENT_ACTION:
            score += 0.2
            reasons.append("действие агента")

        # Короткие сообщения обычно важнее длинных
        if len(content) < 200:
            score += 0.1
            reasons.append("краткое")

        # Нормализуем
        score = max(0.0, min(1.0, score))

        return MessageImportance(score, "; ".join(reasons))

    def _summarize_page_context(self, content: str, max_tokens: int = 200) -> str:
        """
        Сжать контекст страницы до ключевых моментов

        Args:
            content: Полный текст
            max_tokens: Максимум токенов в резюме

        Returns:
            Сжатый текст
        """
        # Если уже короткий - возвращаем как есть
        current_tokens = self._estimate_tokens(content)
        if current_tokens <= max_tokens:
            return content

        # Ищем структурированные данные (списки, меню)
        lines = content.split('\n')
        important_lines = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Сохраняем строки с ценами, названиями блюд, адресами
            if any(marker in line.lower() for marker in ['₽', 'руб', 'адрес:', 'телефон:', '—', ':', 'https://']):
                important_lines.append(line)

            # Ограничиваем размер
            if self._estimate_tokens('\n'.join(important_lines)) >= max_tokens:
                break

        if important_lines:
            return "[СЖАТО]\n" + '\n'.join(important_lines[:30])  # Макс 30 строк

        # Если не нашли структуру - берём начало
        words = content.split()[:100]
        return "[СЖАТО] " + ' '.join(words) + "..."

    def _summarize_action_sequence(self, messages: List[Dict[str, str]]) -> str:
        """
        Сжать последовательность действий агента в краткую сводку

        Args:
            messages: Список сообщений агента

        Returns:
            Краткая сводка действий
        """
        actions = []
        for msg in messages:
            content = msg.get("content", "")
            # Извлекаем название действия из JSON
            match = re.search(r'"action":\s*"([^"]+)"', content)
            if match:
                action_name = match.group(1)
                # Извлекаем reasoning если есть
                reasoning_match = re.search(r'"reasoning":\s*"([^"]+)"', content)
                reasoning = reasoning_match.group(1) if reasoning_match else ""
                actions.append(f"{action_name}: {reasoning}")

        if actions:
            return "[ПОСЛЕДОВАТЕЛЬНОСТЬ ДЕЙСТВИЙ]\n" + '\n'.join(actions)
        return ""

    def compress_conversation(
        self,
        history: List[Dict[str, str]],
        target_tokens: int,
        preserve_recent: int = 4
    ) -> List[Dict[str, str]]:
        """
        Сжать историю разговора с сохранением важной информации

        Args:
            history: Полная история разговора
            target_tokens: Целевое количество токенов
            preserve_recent: Сколько последних сообщений всегда сохранять

        Returns:
            Сжатая история
        """
        if len(history) <= 2:  # Системный промпт + 1 сообщение
            return history

        self.compression_stats['original_count'] = len(history)

        # Разделяем на части
        system_prompt = history[0] if history and history[0].get("role") == "system" else None
        recent_messages = history[-preserve_recent:] if preserve_recent > 0 else []
        middle_messages = history[1:-preserve_recent] if preserve_recent > 0 else history[1:]

        # Классифицируем и оцениваем важность средних сообщений
        scored_messages = []
        total_middle = len(middle_messages)
        for idx, msg in enumerate(middle_messages):
            msg_type = self._classify_message(msg)
            # Рассчитываем позицию с конца (включая recent_messages)
            position_from_end = total_middle - idx + preserve_recent
            importance = self._calculate_importance(msg, msg_type, position_from_end)
            scored_messages.append({
                'message': msg,
                'type': msg_type,
                'importance': importance,
                'tokens': self._estimate_tokens(msg.get('content', ''))
            })

        # Сортируем по важности
        scored_messages.sort(key=lambda x: x['importance'].score, reverse=True)

        # Собираем сжатый контекст
        compressed = []
        if system_prompt:
            compressed.append(system_prompt)

        # Добавляем сообщения по важности пока не достигнем лимита
        current_tokens = self._estimate_tokens(system_prompt.get('content', '')) if system_prompt else 0
        current_tokens += sum(self._estimate_tokens(m.get('content', '')) for m in recent_messages)

        # Резервируем место для недавних сообщений
        available_tokens = target_tokens - current_tokens

        page_contexts = []
        action_sequences = []

        for item in scored_messages:
            msg = item['message']
            msg_tokens = item['tokens']
            msg_type = item['type']

            # Сжимаем большие контексты страниц
            if msg_type == MessageType.PAGE_CONTEXT or msg_tokens > 500:
                page_contexts.append(msg)
                continue

            # Группируем последовательности действий
            if msg_type == MessageType.AGENT_ACTION:
                action_sequences.append(msg)
                continue

            # Добавляем важные сообщения как есть
            if item['importance'].score >= 0.5 and current_tokens + msg_tokens < available_tokens:
                compressed.append(msg)
                current_tokens += msg_tokens

        # Добавляем сжатый контекст страниц (последний самый актуальный)
        if page_contexts and current_tokens < available_tokens:
            last_page = page_contexts[-1]
            summarized = self._summarize_page_context(last_page.get('content', ''), max_tokens=300)
            compressed.append({
                'role': last_page.get('role'),
                'content': summarized
            })
            current_tokens += self._estimate_tokens(summarized)

        # Добавляем сжатую последовательность действий
        if action_sequences and current_tokens < available_tokens:
            summary = self._summarize_action_sequence(action_sequences[-5:])  # Последние 5 действий
            if summary:
                compressed.append({
                    'role': 'assistant',
                    'content': summary
                })
                current_tokens += self._estimate_tokens(summary)

        # Добавляем последние сообщения
        compressed.extend(recent_messages)

        # Статистика
        original_tokens = sum(self._estimate_tokens(m.get('content', '')) for m in history)
        compressed_tokens = sum(self._estimate_tokens(m.get('content', '')) for m in compressed)

        self.compression_stats['compressed_count'] = len(compressed)
        self.compression_stats['tokens_saved'] = original_tokens - compressed_tokens

        return compressed

    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику компрессии"""
        return self.compression_stats.copy()
