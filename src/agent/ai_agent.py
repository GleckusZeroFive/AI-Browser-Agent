import json
import time
import logging
import base64
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from openai import OpenAI
from src.config import Config, ModelType
from src.prompts import PromptManager, PromptLevel, AgentType
from src.agent.context_compressor import ContextCompressor
from src.agent.knowledge_base import ContextLevel

class AIAgent:
    """Универсальный AI агент для автоматизации браузера с умным выбором модели"""

    def __init__(self, agent_type: AgentType = AgentType.GENERAL):
        self.client = OpenAI(
            api_key=Config.get_api_key(),
            base_url=Config.get_base_url()
        )
        self.current_model = Config.DEFAULT_MODEL
        self.conversation_history: List[Dict[str, str]] = []
        self.current_plan: List[str] = []
        self.last_request_time = 0
        self.rate_limit_count = 0  # Счётчик rate limit ошибок
        self._keys_tried_this_request = 0  # Сколько ключей попробовали в текущем запросе
        self.logger = logging.getLogger(__name__)

        # Логируем количество доступных ключей
        keys_count = Config.get_api_keys_count()
        if keys_count > 1:
            self.logger.info(f"Доступно {keys_count} API ключей для ротации")

        # Новые компоненты
        self.prompt_manager = PromptManager()
        self.context_compressor = ContextCompressor()
        self.agent_type = agent_type

        # Атрибуты для управления контекстом
        self.task_type: Optional[str] = None
        self._current_context_level: ContextLevel = ContextLevel.COMPACT
        self._current_prompt_level: PromptLevel = PromptLevel.COMPACT
        self._cached_system_prompt: Optional[str] = None
        self._cached_prompt_level: Optional[PromptLevel] = None
        self.knowledge_base = None  # Будет установлен извне

    def _estimate_tokens(self, text) -> int:
        """
        Приблизительная оценка количества токенов в тексте

        Используем эвристику: ~4 символа = 1 токен для английского текста
        Для русского текста: ~2.5 символа = 1 токен (кириллица кодируется менее эффективно)

        Args:
            text: текст для оценки (строка или список для Vision API)

        Returns:
            Примерное количество токенов
        """
        if not text:
            return 0

        # Обработка Vision API формата (список с текстом и изображениями)
        if isinstance(text, list):
            total = 0
            for item in text:
                if isinstance(item, dict):
                    if item.get("type") == "text":
                        total += self._estimate_tokens(item.get("text", ""))
                    elif item.get("type") == "image_url":
                        # Изображение ~200-300 токенов
                        total += 250
                elif isinstance(item, str):
                    total += self._estimate_tokens(item)
            return total

        # Если это не строка, пропускаем
        if not isinstance(text, str):
            return 0

        # Подсчитываем кириллицу и латиницу отдельно
        cyrillic_count = sum(1 for c in text if '\u0400' <= c <= '\u04FF')
        total_chars = len(text)
        latin_count = total_chars - cyrillic_count

        # Кириллица: ~2.5 символа на токен, латиница: ~4 символа на токен
        estimated_tokens = (cyrillic_count / 2.5) + (latin_count / 4.0)

        return int(estimated_tokens)

    def _calculate_context_tokens(self) -> int:
        """
        Подсчитать общее количество токенов в контексте разговора

        Returns:
            Общее количество токенов
        """
        total_tokens = 0
        for message in self.conversation_history:
            content = message.get("content", "")
            total_tokens += self._estimate_tokens(content)

        return total_tokens

    def _trim_conversation_history(self, max_tokens: int):
        """
        Интеллектуальное сжатие истории разговора с сохранением важной информации

        Args:
            max_tokens: максимальное количество токенов
        """
        if len(self.conversation_history) <= 2:
            return  # Не трогаем если только системный промпт и одно сообщение

        old_count = len(self.conversation_history)
        old_tokens = self._calculate_context_tokens()

        # Используем интеллектуальную компрессию
        self.conversation_history = self.context_compressor.compress_conversation(
            history=self.conversation_history,
            target_tokens=max_tokens,
            preserve_recent=Config.CONTEXT_TRIM_TO  # Сохраняем последние N
        )

        # Обновляем системный промпт на более компактный
        if self.conversation_history and self.conversation_history[0].get("role") == "system":
            current_tokens = self._calculate_context_tokens()
            compact_prompt = self.prompt_manager.get_system_prompt(
                agent_type=self.agent_type,
                context_size=current_tokens
            )
            self.conversation_history[0]["content"] = compact_prompt

        new_tokens = self._calculate_context_tokens()
        stats = self.context_compressor.get_stats()

        self.logger.info(
            f"Контекст сжат: {old_count} -> {len(self.conversation_history)} сообщений, "
            f"{old_tokens} -> {new_tokens} токенов (экономия: {stats.get('tokens_saved', 0)} токенов)"
        )

        print(f"💾 Контекст сжат: {old_count} -> {len(self.conversation_history)} сообщений "
              f"({old_tokens} -> {new_tokens} токенов)")

    def add_system_prompt(self):
        """Добавить динамический системный промпт"""
        # Генерируем промпт с учётом типа агента
        # Начинаем с полного промпта, потом будем адаптировать на основе контекста
        system_prompt = self.prompt_manager.get_system_prompt(
            level=PromptLevel.COMPACT,  # Начинаем с компактного
            agent_type=self.agent_type
        )

        self.conversation_history.append({
            "role": "system",
            "content": system_prompt
        })

        # Логируем статистику
        tokens = self._estimate_tokens(system_prompt)
        self.logger.info(f"Системный промпт загружен: {tokens} токенов (тип: {self.agent_type.value})")

    def _select_model_for_request(self, message: str, context: str = None) -> str:
        """Выбрать подходящую модель для запроса"""
        # Если много rate limit ошибок - используем быструю модель
        if self.rate_limit_count >= 2:
            return Config.MODELS[ModelType.FAST]

        # Для анализа больших страниц используем быструю модель
        if context and len(context) > 2000:
            return Config.MODELS[ModelType.FAST]

        # Для первого запроса и планирования - умная модель
        if len(self.conversation_history) <= 2:
            return Config.MODELS[ModelType.FAST]  # Начинаем с быстрой

        return self.current_model

    def _enforce_rate_limit(self):
        """Соблюдать минимальный интервал между запросами"""
        elapsed = time.time() - self.last_request_time
        if elapsed < Config.MIN_REQUEST_INTERVAL:
            time.sleep(Config.MIN_REQUEST_INTERVAL - elapsed)
        self.last_request_time = time.time()

    def _rotate_api_key(self) -> bool:
        """
        Попытаться переключиться на другой API ключ при rate limit.
        Возвращает True если удалось, False если ключи закончились.
        """
        keys_count = Config.get_api_keys_count()

        if keys_count <= 1:
            return False

        # Проверяем, не попробовали ли мы уже все ключи
        if self._keys_tried_this_request >= keys_count:
            self.logger.warning("Все API ключи достигли rate limit")
            return False

        # Переключаемся на следующий ключ
        old_index = Config.get_current_key_index()
        if Config.rotate_api_key():
            new_index = Config.get_current_key_index()
            self._keys_tried_this_request += 1

            # Пересоздаём клиент с новым ключом
            self.client = OpenAI(
                api_key=Config.get_current_api_key(),
                base_url=Config.get_base_url()
            )

            self.logger.info(f"Переключение API ключа: {old_index} → {new_index} (из {keys_count})")
            print(f"🔄 Переключаюсь на API ключ #{new_index} из {keys_count}...")
            return True

        return False

    def _reset_keys_tried(self):
        """Сбросить счётчик попробованных ключей (вызывать при успешном запросе)"""
        self._keys_tried_this_request = 0

    def _get_suitable_fallback_model(self, current_tokens: int, exclude_model: str = None) -> Optional[str]:
        """
        Выбрать подходящую fallback-модель с учетом размера контекста

        Args:
            current_tokens: текущий размер контекста в токенах
            exclude_model: модель которую нужно исключить

        Returns:
            Название модели или None
        """
        suitable_models = []

        for model in Config.FALLBACK_MODELS:
            if model == exclude_model:
                continue

            model_limit = Config.MODEL_TOKEN_LIMITS.get(model, 6000)
            safe_limit = int(model_limit * Config.SAFE_TOKEN_MARGIN)

            if current_tokens <= safe_limit:
                suitable_models.append((model, model_limit))

        if not suitable_models:
            return None

        # Возвращаем модель с наибольшим лимитом
        suitable_models.sort(key=lambda x: x[1], reverse=True)
        return suitable_models[0][0]

    def chat(
        self,
        user_message: str,
        context: Optional[str] = None,
        specialized_agent: Optional[Any] = None
    ) -> str:
        """
        Основной метод для общения с AI

        Args:
            user_message: Сообщение пользователя
            context: Дополнительный контекст (например, текст страницы)
            specialized_agent: Специализированный агент (для выбора промпта)

        Returns:
            Ответ AI агента
        """
        # 1. Выбираем модель
        model_to_use = self._select_model_for_request(user_message, context)

        # 2. Подготавливаем полное сообщение с контекстом из KB
        full_message = self._prepare_context_for_request(
            user_message,
            model_to_use,
            specialized_agent
        )

        # 3. Если есть дополнительный контекст страницы - добавляем его
        if context:
            full_message = f"{full_message}\n\nКонтекст страницы:\n{context[:2000]}"

        # 4. Добавляем в историю
        self.conversation_history.append({
            "role": "user",
            "content": full_message
        })

        # 5. Вычисляем текущий размер контекста
        current_tokens = self._calculate_context_tokens()

        # 6. Проверяем не превысили ли лимит ПОСЛЕ добавления
        model_limit = Config.MODEL_TOKEN_LIMITS.get(model_to_use, 6000)
        safe_limit = int(model_limit * Config.SAFE_TOKEN_MARGIN)

        if current_tokens > safe_limit:
            self.logger.warning(
                f"Превышен лимит токенов: {current_tokens} > {safe_limit}. "
                f"Сокращаю историю."
            )
            self._trim_conversation_history(safe_limit)
            current_tokens = self._calculate_context_tokens()

        # Список моделей для fallback
        models_to_try = [model_to_use] + [m for m in Config.FALLBACK_MODELS if m != model_to_use]

        for model in models_to_try:
            try:
                # Соблюдаем rate limit
                self._enforce_rate_limit()

                self.logger.info(f"Запрос к модели: {model}")

                response = self.client.chat.completions.create(
                    model=model,
                    messages=self.conversation_history,
                    temperature=Config.TEMPERATURE,
                    max_tokens=Config.MAX_TOKENS,
                )

                assistant_message = response.choices[0].message.content

                self.conversation_history.append({
                    "role": "assistant",
                    "content": assistant_message
                })

                # Успешный запрос - сбрасываем счётчики
                self.rate_limit_count = 0
                self._reset_keys_tried()
                self.current_model = model

                return assistant_message

            except Exception as e:
                error_str = str(e)
                error_type = type(e).__name__

                # Ошибка 413 - контекст слишком большой для модели
                if "413" in error_str or "payload too large" in error_str.lower() or "request too large" in error_str.lower():
                    self.logger.warning(f"Контекст слишком большой для модели {model}")

                    # Сокращаем контекст
                    model_limit = Config.MODEL_TOKEN_LIMITS.get(model, 6000)
                    safe_limit = int(model_limit * Config.SAFE_TOKEN_MARGIN)
                    self._trim_conversation_history(safe_limit)

                    # Пробуем найти модель с большим лимитом для следующей попытки
                    current_tokens = self._calculate_context_tokens()
                    alternative_model = self._get_suitable_fallback_model(current_tokens, exclude_model=model)

                    if alternative_model:
                        self.logger.info(f"Переключаюсь на модель с большим лимитом: {alternative_model}")
                        print(f"💾 Контекст сокращен, переключаюсь на модель с большим лимитом...")
                        # Перемещаем альтернативную модель в начало списка
                        if alternative_model in models_to_try:
                            models_to_try.remove(alternative_model)
                            models_to_try.insert(models_to_try.index(model) + 1, alternative_model)
                    continue

                # Rate limit - сначала пробуем другой API ключ, потом другую модель
                if "429" in error_str or "rate limit" in error_str.lower():
                    self.rate_limit_count += 1

                    # Проверяем: это дневной лимит (TPD) или минутный (TPM)?
                    is_daily_limit = "tokens per day" in error_str.lower() or "tpd" in error_str.lower()

                    if is_daily_limit:
                        # Дневной лимит - пробуем другой API ключ
                        if self._rotate_api_key():
                            self.logger.info("Дневной лимит достигнут, переключаюсь на другой API ключ")
                            # Сбрасываем список моделей и начинаем сначала с новым ключом
                            models_to_try = [model_to_use] + [m for m in Config.FALLBACK_MODELS if m != model_to_use]
                            continue
                        else:
                            # Все ключи исчерпаны
                            self.logger.error("Все API ключи достигли дневного лимита")
                            return (
                                "❌ Все API ключи достигли дневного лимита Groq (500k токенов/день).\n\n"
                                "Варианты решения:\n"
                                "1. Подождите до сброса лимита (обычно в полночь UTC)\n"
                                "2. Добавьте больше API ключей в .env:\n"
                                "   GROQ_API_KEY_2=ваш_ключ\n"
                                "   GROQ_API_KEY_3=ваш_ключ\n"
                                "3. Перейдите на платный тариф Groq\n"
                            )

                    # Минутный лимит - пробуем другую модель
                    remaining_models = [m for m in models_to_try if m != model and models_to_try.index(m) > models_to_try.index(model)]
                    if remaining_models:
                        self.logger.warning(f"⚠️ Rate limit для {model}, переключаюсь на {remaining_models[0]}")
                        print(f"⚠️ Rate limit достигнут, переключаюсь на другую модель...")
                    else:
                        # Все модели исчерпаны, пробуем другой ключ
                        if self._rotate_api_key():
                            models_to_try = [model_to_use] + [m for m in Config.FALLBACK_MODELS if m != model_to_use]
                            continue
                        self.logger.warning(f"⚠️ Rate limit для {model}, это последняя модель и последний ключ")
                    time.sleep(Config.RATE_LIMIT_RETRY_DELAY)
                    continue

                # Модель недоступна - пробуем следующую
                if "404" in error_str or "not found" in error_str.lower():
                    self.logger.warning(f"Модель {model} недоступна, пробую следующую")
                    continue

                # API key проблемы
                if "401" in error_str or "unauthorized" in error_str.lower() or "invalid api key" in error_str.lower():
                    self.logger.error(f"Ошибка авторизации API: {e}")
                    return (
                        "❌ Ошибка авторизации API (неверный API ключ).\n\n"
                        "Проверьте ваш GROQ_API_KEY в файле .env:\n"
                        "1. Убедитесь что ключ правильный\n"
                        "2. Проверьте что ключ активен на https://console.groq.com\n"
                        "3. Попробуйте создать новый ключ\n\n"
                        f"Детали ошибки: {error_str}"
                    )

                # Сетевые ошибки
                if "connection" in error_str.lower() or "network" in error_str.lower() or "timeout" in error_str.lower():
                    self.logger.error(f"Ошибка сети: {e}")
                    return (
                        f"❌ Ошибка подключения к API ({error_type}).\n\n"
                        "Возможные причины:\n"
                        "- Отсутствует интернет-соединение\n"
                        "- API сервис временно недоступен\n"
                        "- Проблемы с сетью\n\n"
                        "Попробуйте:\n"
                        "1. Проверить интернет-соединение\n"
                        "2. Повторить запрос через несколько секунд\n\n"
                        f"Детали: {error_str}"
                    )

                # Другая ошибка - возвращаем с подробностями
                self.logger.error(f"Ошибка API ({error_type}): {e}", exc_info=True)
                return (
                    f"❌ Ошибка API ({error_type}).\n"
                    f"Детали: {error_str}\n\n"
                    "Попробуйте повторить запрос или обратитесь к документации API."
                )

        # Все модели недоступны
        self.logger.error("Все модели недоступны после нескольких попыток")
        return (
            "❌ Все доступные модели недоступны или достигнут rate limit.\n\n"
            "Возможные причины:\n"
            "- Достигнут лимит запросов на все модели\n"
            "- Сервис Groq временно недоступен\n"
            "- Проблемы с API ключом\n\n"
            "Попробуйте:\n"
            "1. Подождать несколько минут и повторить\n"
            "2. Проверить статус на https://status.groq.com\n"
            "3. Проверить лимиты вашего API ключа на https://console.groq.com"
        )

    def parse_action(self, response: str) -> Optional[Dict[str, Any]]:
        """
        Попытаться распарсить JSON действие из ответа

        Извлекает ПЕРВЫЙ валидный JSON с полем "action" из ответа.
        Игнорирует последующие JSON если агент их написал (галлюцинация).
        """
        try:
            import re

            # Ищем ВСЕ JSON объекты в ответе
            # Паттерн: { ... } с учётом вложенности
            json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            json_matches = re.finditer(json_pattern, response, re.DOTALL)

            # Пробуем распарсить каждый найденный JSON
            for match in json_matches:
                json_str = match.group()

                # Пробуем стандартный парсинг
                try:
                    action = json.loads(json_str)

                    # Проверяем что это действие
                    if "action" in action and action.get("action"):
                        self.logger.debug(f"Найдено действие: {action.get('action')}")
                        return action

                except json.JSONDecodeError:
                    # LLM иногда генерирует невалидный JSON без кавычек
                    # Пример: {action: navigate, params: {url: "..."}}
                    # Исправляем на: {"action": "navigate", "params": {"url": "..."}}

                    # Шаг 1: Добавляем кавычки к ключам: action: -> "action":
                    fixed = re.sub(r'(\{|,)\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', json_str)

                    # Шаг 2: Добавляем кавычки к значениям без кавычек (только простые значения, не url)
                    # Паттерн: "key": value -> "key": "value" (только для слов, не для чисел и true/false/null)
                    fixed = re.sub(
                        r':\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*([,}])',
                        r': "\1"\2',
                        fixed
                    )

                    # Шаг 3: Заменяем одинарные кавычки на двойные
                    fixed = fixed.replace("'", '"')

                    try:
                        action = json.loads(fixed)

                        # Проверяем что это действие
                        if "action" in action and action.get("action"):
                            self.logger.debug(f"Найдено действие (после исправления): {action.get('action')}")
                            return action
                    except json.JSONDecodeError:
                        # Этот JSON не валиден - пробуем следующий
                        continue

            # Не нашли ни одного валидного действия
            return None

        except Exception as e:
            self.logger.error(f"Ошибка при парсинге действия: {e}", exc_info=True)
            return None

    def get_token_usage_stats(self) -> Dict[str, Any]:
        """
        Возвращает статистику использования токенов

        Returns:
            Словарь со статистикой
        """
        model_limit = Config.MODEL_TOKEN_LIMITS.get(self.current_model, 6000)
        used_tokens = self._calculate_context_tokens()
        safe_limit = int(model_limit * Config.SAFE_TOKEN_MARGIN)

        # Рассчитываем экономию
        # Если бы использовали FULL везде
        if self.knowledge_base:
            full_kb = self.knowledge_base.estimate_tokens(ContextLevel.FULL, self.task_type)
            current_kb = self.knowledge_base.estimate_tokens(
                self._current_context_level,
                self.task_type
            )
            kb_savings = ((full_kb - current_kb) / full_kb * 100) if full_kb > 0 else 0
        else:
            kb_savings = 0

        return {
            "model": self.current_model,
            "model_limit": model_limit,
            "safe_limit": safe_limit,
            "used_tokens": used_tokens,
            "available_tokens": safe_limit - used_tokens,
            "usage_percent": (used_tokens / safe_limit * 100) if safe_limit > 0 else 0,
            "context_level": self._current_context_level.value,
            "prompt_level": self._current_prompt_level.value,
            "kb_savings_percent": round(kb_savings, 1),
            "task_type": self.task_type
        }

    def reset_conversation(self):
        """Сбросить историю разговора"""
        self.conversation_history = []
        self.current_plan = []
        self.add_system_prompt()

    def _encode_image_to_base64(self, image_path: str) -> str:
        """
        Кодирует изображение в base64 для отправки в Vision API

        Args:
            image_path: путь к изображению

        Returns:
            Base64-строка изображения
        """
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            self.logger.error(f"Ошибка при кодировании изображения: {e}")
            raise

    def chat_with_vision(
        self,
        user_message: str,
        image_path: Optional[str] = None,
        specialized_agent: Optional[Any] = None
    ) -> str:
        """
        Общение с AI используя Vision-модель для анализа скриншотов

        Args:
            user_message: Сообщение пользователя/запрос
            image_path: Путь к скриншоту страницы (опционально)
            specialized_agent: Специализированный агент

        Returns:
            Ответ AI агента
        """
        # Используем Vision-модель
        vision_model = Config.VISION_MODEL

        # Подготавливаем сообщение с контекстом из KB
        full_message = self._prepare_context_for_request(
            user_message,
            vision_model,
            specialized_agent
        )

        # Формируем content для сообщения
        content_parts = [{"type": "text", "text": full_message}]

        # Если есть изображение - добавляем его
        if image_path and Path(image_path).exists():
            try:
                image_base64 = self._encode_image_to_base64(image_path)
                content_parts.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{image_base64}"
                    }
                })
                self.logger.info(f"Добавлен скриншот к запросу: {image_path}")
            except Exception as e:
                self.logger.warning(f"Не удалось добавить изображение: {e}")

        # Добавляем в историю
        self.conversation_history.append({
            "role": "user",
            "content": content_parts
        })

        # Проверяем размер контекста
        current_tokens = self._calculate_context_tokens()
        model_limit = Config.MODEL_TOKEN_LIMITS.get(vision_model, 6000)
        safe_limit = int(model_limit * Config.SAFE_TOKEN_MARGIN)

        if current_tokens > safe_limit:
            self.logger.warning(
                f"Превышен лимит токенов: {current_tokens} > {safe_limit}. Сокращаю историю."
            )
            self._trim_conversation_history(safe_limit)
            current_tokens = self._calculate_context_tokens()

        # Отправляем запрос
        try:
            self._enforce_rate_limit()

            self.logger.info(f"Запрос к Vision-модели: {vision_model}")

            response = self.client.chat.completions.create(
                model=vision_model,
                messages=self.conversation_history,
                temperature=Config.TEMPERATURE,
                max_tokens=Config.MAX_TOKENS,
            )

            assistant_message = response.choices[0].message.content

            self.conversation_history.append({
                "role": "assistant",
                "content": assistant_message
            })

            # Успешный запрос
            self.rate_limit_count = 0
            self._reset_keys_tried()
            self.current_model = vision_model

            return assistant_message

        except Exception as e:
            error_str = str(e)
            error_type = type(e).__name__

            self.logger.error(f"Ошибка Vision API ({error_type}): {e}", exc_info=True)

            # Проверяем: это дневной лимит?
            is_daily_limit = "tokens per day" in error_str.lower() or "tpd" in error_str.lower()

            if ("429" in error_str or "rate limit" in error_str.lower()) and is_daily_limit:
                # Пробуем переключить API ключ
                if self._rotate_api_key():
                    # Удаляем Vision-сообщение и повторяем запрос
                    if self.conversation_history and self.conversation_history[-1].get("role") == "user":
                        last_content = self.conversation_history[-1].get("content")
                        if isinstance(last_content, list):
                            self.conversation_history.pop()
                    return self.chat_with_vision(user_message, image_path, specialized_agent)

            # Удаляем последнее сообщение из истории (оно в формате Vision API)
            # чтобы не сломать fallback на текстовую модель
            if self.conversation_history and self.conversation_history[-1].get("role") == "user":
                last_content = self.conversation_history[-1].get("content")
                if isinstance(last_content, list):
                    self.conversation_history.pop()
                    self.logger.info("Удалено Vision-сообщение из истории для fallback")

            # Если Vision-модель недоступна, возвращаемся к текстовой
            self.logger.warning("Vision-модель недоступна, переключаюсь на текстовую модель")
            return self.chat(user_message, specialized_agent=specialized_agent)

    def set_task_type(self, task_type: Optional[str]):
        """
        Устанавливает тип текущей задачи для локализации контекста

        Args:
            task_type: Тип задачи ("shopping", "email", "job_search", None)
        """
        if self.task_type != task_type:
            self.task_type = task_type
            # Инвалидируем кеш промпта при смене типа задачи
            self._cached_prompt_level = None
            self._cached_system_prompt = None
            self.logger.info(f"Тип задачи изменён: {task_type}")

    def _select_context_level(
        self,
        model: str,
        specialized_agent: Optional[Any] = None
    ) -> Tuple[ContextLevel, PromptLevel]:
        """
        Выбирает оптимальные уровни контекста на основе доступных токенов

        Args:
            model: Имя модели для которой выбираем уровни
            specialized_agent: Специализированный агент (если есть)

        Returns:
            Tuple[ContextLevel, PromptLevel] - уровни для KB и промпта
        """
        # 1. Получаем лимит модели
        model_limit = Config.MODEL_TOKEN_LIMITS.get(model, 6000)
        safe_limit = int(model_limit * Config.SAFE_TOKEN_MARGIN)  # 70%

        # 2. Рассчитываем текущее использование токенов
        # (без учёта системного промпта, т.к. мы его можем изменить)
        current_tokens = sum(
            self._estimate_tokens(msg["content"])
            for msg in self.conversation_history
            if msg["role"] != "system"
        )

        # 3. Оцениваем размер контекста KB для разных уровней
        if self.knowledge_base:
            kb_minimal = self.knowledge_base.estimate_tokens(
                ContextLevel.MINIMAL, self.task_type
            )
            kb_compact = self.knowledge_base.estimate_tokens(
                ContextLevel.COMPACT, self.task_type
            )
            kb_full = self.knowledge_base.estimate_tokens(
                ContextLevel.FULL, self.task_type
            )
        else:
            kb_minimal = 100
            kb_compact = 300
            kb_full = 800

        # 4. Оцениваем размер промпта для разных уровней
        if specialized_agent and hasattr(specialized_agent, 'get_system_prompt'):
            prompt_minimal = self._estimate_tokens(
                specialized_agent.get_system_prompt(PromptLevel.MINIMAL)
            )
            prompt_compact = self._estimate_tokens(
                specialized_agent.get_system_prompt(PromptLevel.COMPACT)
            )
            prompt_full = self._estimate_tokens(
                specialized_agent.get_system_prompt(PromptLevel.FULL)
            )
        else:
            # Для general agent используем базовые оценки
            prompt_minimal = 200
            prompt_compact = 400
            prompt_full = 800

        # 5. Резервируем место для ответа модели
        response_reserve = Config.MAX_TOKENS  # 2000 токенов

        # 6. Рассчитываем доступное место
        available = safe_limit - current_tokens - response_reserve

        self.logger.info(
            f"Выбор уровня контекста: model={model}, "
            f"limit={model_limit}, safe={safe_limit}, "
            f"current={current_tokens}, available={available}"
        )

        # 7. Выбираем уровни на основе доступного места
        # Стратегия: пробуем FULL → COMPACT → MINIMAL

        # Пробуем FULL
        full_total = kb_full + prompt_full
        if available >= full_total:
            self.logger.info(
                f"Выбран уровень FULL: KB={kb_full}т + Prompt={prompt_full}т = {full_total}т"
            )
            return (ContextLevel.FULL, PromptLevel.FULL)

        # Пробуем COMPACT
        compact_total = kb_compact + prompt_compact
        if available >= compact_total:
            self.logger.info(
                f"Выбран уровень COMPACT: KB={kb_compact}т + Prompt={prompt_compact}т = {compact_total}т"
            )
            return (ContextLevel.COMPACT, PromptLevel.COMPACT)

        # Используем MINIMAL (минимально необходимый)
        minimal_total = kb_minimal + prompt_minimal
        self.logger.info(
            f"Выбран уровень MINIMAL: KB={kb_minimal}т + Prompt={prompt_minimal}т = {minimal_total}т"
        )

        # Проверяем что даже MINIMAL помещается
        if available < minimal_total:
            self.logger.warning(
                f"Недостаточно места даже для MINIMAL! "
                f"Доступно {available}т, нужно {minimal_total}т. "
                f"Необходимо сократить conversation_history."
            )
            # Принудительно сокращаем историю
            self._trim_conversation_history(safe_limit // 2)

        return (ContextLevel.MINIMAL, PromptLevel.MINIMAL)

    def _update_system_message(self, new_system_prompt: str):
        """
        Обновляет системное сообщение в conversation_history

        Args:
            new_system_prompt: Новый системный промпт
        """
        # Ищем системное сообщение (первое с role="system")
        for i, msg in enumerate(self.conversation_history):
            if msg["role"] == "system":
                # Обновляем
                self.conversation_history[i]["content"] = new_system_prompt
                self.logger.debug(f"Системный промпт обновлён: {len(new_system_prompt)} символов")
                return

        # Если не нашли - добавляем в начало
        self.conversation_history.insert(0, {
            "role": "system",
            "content": new_system_prompt
        })
        self.logger.debug(f"Системный промпт добавлен: {len(new_system_prompt)} символов")

    def _get_base_system_prompt(self, level: PromptLevel) -> str:
        """
        Возвращает базовый системный промпт для general agent

        Args:
            level: Уровень детализации

        Returns:
            Системный промпт
        """
        if level == PromptLevel.MINIMAL:
            return """Ты - AI агент для автоматизации браузера.

Доступные действия: navigate, click_by_text, search_and_type, scroll_down, wait, done.

done: завершить задачу и сообщить результат. Пример: {"action": "done", "params": {"message": "Ответ пользователю"}}

После действий получаешь СКРИНШОТ для анализа.
Формат: текст + JSON команда.

ОТВЕЧАЙ НА РУССКОМ ЯЗЫКЕ."""

        elif level == PromptLevel.COMPACT:
            return """Ты - AI агент для автоматизации браузера.
Отвечай ТОЛЬКО на русском языке.

Доступные действия:
- navigate: переход на URL
- click_by_text: клик по тексту
- search_and_type: поиск и ввод
- scroll_down, scroll_up, wait
- done: ЗАВЕРШИТЬ задачу и сообщить результат пользователю
  Пример: {"action": "done", "params": {"message": "Погода в Москве: -9°, ясно"}}

ВАЖНО: После каждого действия получаешь СКРИНШОТ страницы.
Используй визуальную информацию для принятия решений.
Когда нашёл ответ на вопрос - используй done чтобы сообщить результат!

Формат ответа:
1. Рассуждение для пользователя
2. JSON команда (если нужно действие)

Правила:
- НЕ галлюцинируй - кликай только на видимое на скриншоте
- Используй базу знаний - не переспрашивай
- Помни контекст - не ищи заново

ОТВЕЧАЙ НА РУССКОМ ЯЗЫКЕ."""

        else:  # FULL
            # Используем полный промпт через PromptManager
            return self.prompt_manager.get_system_prompt(
                level=PromptLevel.FULL,
                agent_type=self.agent_type
            )

    def _prepare_context_for_request(
        self,
        user_message: str,
        model: str,
        specialized_agent: Optional[Any] = None
    ) -> str:
        """
        Подготавливает полное сообщение пользователя с контекстом

        Args:
            user_message: Исходное сообщение пользователя
            model: Модель для которой готовим контекст
            specialized_agent: Специализированный агент (если есть)

        Returns:
            Полное сообщение с контекстом из knowledge base
        """
        # 1. Выбираем оптимальные уровни
        context_level, prompt_level = self._select_context_level(model, specialized_agent)

        # Сохраняем для мониторинга
        self._current_context_level = context_level
        self._current_prompt_level = prompt_level

        # 2. Обновляем системный промпт если нужно
        if prompt_level != self._cached_prompt_level:
            if specialized_agent and hasattr(specialized_agent, 'get_system_prompt'):
                new_prompt = specialized_agent.get_system_prompt(prompt_level)
            else:
                # Для general agent используем базовый промпт
                new_prompt = self._get_base_system_prompt(prompt_level)

            self._update_system_message(new_prompt)
            self._cached_system_prompt = new_prompt
            self._cached_prompt_level = prompt_level

        # 3. Получаем контекст из knowledge base
        if self.knowledge_base:
            kb_context = self.knowledge_base.get_context_summary(
                level=context_level,
                task_type=self.task_type
            )

            # Добавляем контекст к сообщению
            full_message = f"{kb_context}\n\nПользователь: {user_message}"
        else:
            full_message = user_message

        self.logger.info(
            f"Контекст подготовлен: context={context_level.value}, "
            f"prompt={prompt_level.value}, "
            f"message_size={len(full_message)} символов"
        )

        return full_message
