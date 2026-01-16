"""
Knowledge Base - база знаний агента о пользователе и мире

Агент самостоятельно формирует и обновляет базу знаний:
1. Информация о пользователе (предпочтения, город, аллергии и т.д.)
2. Проверенные факты (существующие рестораны, цены, адреса)
3. История взаимодействий (что пользователь любит/не любит)

Цель: избежать повторных вопросов и галлюцинаций
"""
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
from openai import OpenAI
from enum import Enum


class ContextLevel(Enum):
    """Уровни детализации контекста для оптимизации использования токенов"""
    MINIMAL = "minimal"    # ~100 токенов: только критическое (город, аллергии)
    COMPACT = "compact"    # ~300 токенов: базовая инфо + предпочтения
    FULL = "full"          # ~800+ токенов: весь контекст


class KnowledgeBase:
    """
    База знаний агента с автоматическим обновлением

    Структура базы знаний:
    {
        "user_info": {
            "location": "Красноярск",
            "dietary_restrictions": ["аллергия на морепродукты"],
            "budget_preferences": {"food": 500},
            "preferences": {
                "food_types": ["итальянская кухня", "пицца"],
                "response_format": "краткий прогноз погоды без лишних деталей"
            }
        },
        "verified_facts": {
            "restaurants": {
                "Красноярск": ["Додо Пицца", "Суши Wok", "KFC"]
            },
            "services": {
                "доставка_пиццы": ["Додопицца (dodopizza.ru)"]
            }
        },
        "interaction_history": {
            "asked_questions": ["погода в Красноярске", "заказ пиццы"],
            "confirmed_facts": ["любит итальянскую кухню"],
            "rejected_suggestions": []
        }
    }
    """

    def __init__(self, llm_client: OpenAI, storage_path: str = "data/knowledge_base.json"):
        """
        Инициализация базы знаний

        Args:
            llm_client: клиент для LLM запросов
            storage_path: путь для сохранения базы знаний
        """
        self.llm = llm_client
        self.storage_path = Path(storage_path)
        self.logger = logging.getLogger(__name__)

        # Создаем директорию если её нет
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Загружаем или создаем базу знаний
        self.knowledge = self._load_or_create()

    def _load_or_create(self) -> Dict[str, Any]:
        """Загрузить существующую базу или создать новую"""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    knowledge = json.load(f)
                    self.logger.info(f"База знаний загружена из {self.storage_path}")
                    return knowledge
            except Exception as e:
                self.logger.error(f"Ошибка загрузки базы знаний: {e}")

        # Создаем новую базу
        self.logger.info("Создается новая база знаний")
        return {
            "user_info": {
                "location": None,
                "dietary_restrictions": [],
                "budget_preferences": {}
            },
            "verified_facts": {
                "restaurants": {},
                "services": {},
                "locations": {}
            },
            "interaction_history": {
                "confirmed_facts": [],
                "rejected_suggestions": []
            },
            "working_memory": {
                "current_task": None,  # "заказываю Маргариту из Додопиццы"
                "current_page": None,  # "на странице меню Додопиццы"
                "shown_options": [],   # ["Маргарита 490₽", "Маргарита с томатным соусом 520₽"]
                "last_action": None,   # "показал варианты пиццы"
                "context": {}          # произвольный контекст для текущей задачи
            },
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "version": "1.1"
            }
        }

    def save(self):
        """Сохранить базу знаний на диск"""
        try:
            self.knowledge["metadata"]["last_updated"] = datetime.now().isoformat()
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(self.knowledge, f, ensure_ascii=False, indent=2)
            self.logger.debug(f"База знаний сохранена в {self.storage_path}")
        except Exception as e:
            self.logger.error(f"Ошибка сохранения базы знаний: {e}")

    async def extract_and_update(self, user_msg: str, agent_response: str):
        """
        Извлечь информацию ТОЛЬКО из сообщения пользователя и обновить базу знаний.

        ВАЖНО: Мы НЕ извлекаем факты из ответа агента, потому что агент может
        галлюцинировать (выдумывать рестораны, цены и т.д.). Факты должны
        добавляться только после реальной проверки на сайте.

        Args:
            user_msg: сообщение пользователя
            agent_response: ответ агента (используется только для контекста вопросов)
        """
        extraction_prompt = f"""Проанализируй сообщение пользователя и извлеки ТОЛЬКО критически важную информацию.

USER: {user_msg}

Извлеки ТОЛЬКО если ЯВНО указано:

1. **user_info** - критическая информация:
   - location: город (например: "в Красноярске", "живу в Москве")
   - dietary_restrictions: аллергии/ограничения (например: "аллергия на орехи", "вегетарианец")
   - budget_preferences: бюджет ТОЛЬКО с конкретной суммой (например: "до 500 рублей")

2. **interaction_history**:
   - confirmed_facts: явные подтверждения ("да", "подойдёт", "беру это")
   - rejected_suggestions: явные отказы ("нет", "не хочу", "другое")

НЕ ИЗВЛЕКАЙ:
- "preferences" - предпочтения в еде из запросов ("хочу пиццу" это НЕ предпочтение)
- "asked_questions" - вопросы пользователя не нужны
- Факты о ресторанах, ценах, товарах

JSON формат:
{{
  "user_info": {{"location": "...", "dietary_restrictions": [], "budget_preferences": {{}}}},
  "interaction_history": {{"confirmed_facts": [], "rejected_suggestions": []}}
}}

Если ничего критичного - верни {{}}.
ТОЛЬКО JSON."""

        try:
            response = self.llm.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[{"role": "user", "content": extraction_prompt}],
                temperature=0.2,
                max_tokens=800,
            )

            response_text = response.choices[0].message.content
            extracted = self._parse_json_safely(response_text)

            if extracted:
                self._merge_knowledge(extracted)
                self.save()

        except Exception as e:
            self.logger.warning(f"Ошибка извлечения знаний: {e}")

    def _merge_knowledge(self, new_knowledge: Dict[str, Any]):
        """
        Слияние новых знаний с существующими

        Args:
            new_knowledge: новая извлеченная информация
        """
        # Обновляем user_info
        if "user_info" in new_knowledge:
            for key, value in new_knowledge["user_info"].items():
                if value:
                    if isinstance(value, list):
                        # Для списков - добавляем уникальные элементы
                        existing = self.knowledge["user_info"].get(key, [])
                        if not isinstance(existing, list):
                            existing = []
                        self.knowledge["user_info"][key] = list(set(existing + value))
                    elif isinstance(value, dict):
                        # Для словарей - обновляем
                        existing = self.knowledge["user_info"].get(key, {})
                        if isinstance(existing, dict):
                            existing.update(value)
                            self.knowledge["user_info"][key] = existing
                        elif isinstance(existing, list):
                            # Если было список, а пришёл словарь - заменяем
                            self.logger.warning(
                                f"Конвертация: {key} из list в dict"
                            )
                            self.knowledge["user_info"][key] = value
                        else:
                            self.knowledge["user_info"][key] = value
                    else:
                        # Простые значения - перезаписываем
                        old_value = self.knowledge["user_info"].get(key)
                        if old_value != value:
                            self.logger.info(
                                f"Обновлено: user_info.{key} = {value} "
                                f"(было: {old_value})"
                            )
                        self.knowledge["user_info"][key] = value

        # Обновляем verified_facts
        if "verified_facts" in new_knowledge:
            for category, facts in new_knowledge["verified_facts"].items():
                if not facts:
                    continue

                if category not in self.knowledge["verified_facts"]:
                    self.knowledge["verified_facts"][category] = {}

                if isinstance(facts, dict):
                    for key, items in facts.items():
                        if key not in self.knowledge["verified_facts"][category]:
                            self.knowledge["verified_facts"][category][key] = []

                        # Добавляем уникальные элементы
                        existing = self.knowledge["verified_facts"][category][key]
                        if isinstance(items, list):
                            new_items = [item for item in items if item not in existing]
                            if new_items:
                                self.logger.info(
                                    f"Добавлены факты: {category}.{key} += {new_items}"
                                )
                                self.knowledge["verified_facts"][category][key].extend(new_items)

        # Обновляем interaction_history
        if "interaction_history" in new_knowledge:
            for key, items in new_knowledge["interaction_history"].items():
                if not items:
                    continue

                if key not in self.knowledge["interaction_history"]:
                    self.knowledge["interaction_history"][key] = []

                # Добавляем уникальные элементы
                existing = self.knowledge["interaction_history"][key]
                if isinstance(items, list):
                    new_items = [item for item in items if item not in existing]
                    if new_items:
                        self.knowledge["interaction_history"][key].extend(new_items)

    def _parse_json_safely(self, response: str) -> Optional[Dict[str, Any]]:
        """Безопасный парсинг JSON из ответа LLM"""
        response = response.strip()

        # Убираем markdown блоки
        if "```" in response:
            import re
            match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
            if match:
                response = match.group(1)

        # Ищем JSON
        if not response.startswith("{"):
            import re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                response = match.group(0)

        try:
            return json.loads(response)
        except json.JSONDecodeError as e:
            self.logger.warning(f"JSON parse error: {e}")
            return None

    def get_context_summary(
        self,
        level: ContextLevel = ContextLevel.COMPACT,
        task_type: Optional[str] = None
    ) -> str:
        """
        Получить краткое резюме базы знаний для передачи агенту

        Args:
            level: Уровень детализации контекста (MINIMAL/COMPACT/FULL)
            task_type: Тип задачи для локализации контекста (shopping/email/job_search/None)

        Returns:
            Отформатированная строка с важной информацией
        """
        # Логируем генерацию контекста
        estimated_tokens = self.estimate_tokens(level, task_type)
        self.logger.info(
            f"Генерация контекста: level={level.value}, task_type={task_type}, "
            f"tokens≈{estimated_tokens}"
        )

        user_info = self.knowledge["user_info"]
        verified = self.knowledge["verified_facts"]
        history = self.knowledge["interaction_history"]

        if level == ContextLevel.MINIMAL:
            return self._generate_minimal_context(user_info)
        elif level == ContextLevel.COMPACT:
            return self._generate_compact_context(user_info, verified, history, task_type)
        else:  # ContextLevel.FULL
            return self._generate_full_context(user_info, verified, history)

    def _generate_minimal_context(self, user_info: Dict[str, Any]) -> str:
        """
        Генерация минимального контекста (~150 токенов)
        Критическая информация: город, аллергии + ТЕКУЩАЯ ЗАДАЧА
        """
        lines = []

        # WORKING MEMORY (самое важное!)
        wm = self.knowledge.get("working_memory", {})
        if wm.get("current_task"):
            lines.append(f"🎯 ТЕКУЩАЯ ЗАДАЧА: {wm['current_task']}")
        if wm.get("current_page"):
            lines.append(f"📄 ГДЕ ТЫ: {wm['current_page']}")
        if wm.get("shown_options"):
            lines.append(f"📋 ПОКАЗАЛ ВАРИАНТЫ: {', '.join(wm['shown_options'][:3])}")

        # Местоположение
        if user_info.get("location"):
            lines.append(f"📍 Местоположение: {user_info['location']}")

        # Аллергии и ограничения питания
        if user_info.get("dietary_restrictions"):
            restrictions = ", ".join(user_info["dietary_restrictions"])
            lines.append(f"⚠️  Аллергии: {restrictions}")
        else:
            lines.append("⚠️  Аллергии: нет")

        # Обязательный язык-якорь
        lines.append("\nОтвечай на русском языке.")

        return "\n".join(lines)

    def _generate_compact_context(
        self,
        user_info: Dict[str, Any],
        verified: Dict[str, Any],
        history: Dict[str, Any],
        task_type: Optional[str]
    ) -> str:
        """
        Генерация компактного контекста (~400 токенов)
        WORKING MEMORY + минимальная инфо + предпочтения + отфильтрованные факты
        """
        lines = []

        # WORKING MEMORY (КРИТИЧНО для решения проблемы!)
        wm = self.knowledge.get("working_memory", {})
        if wm.get("current_task"):
            lines.append(f"🎯 ТЕКУЩАЯ ЗАДАЧА: {wm['current_task']}")
        if wm.get("current_page"):
            lines.append(f"📄 ГДЕ ТЫ СЕЙЧАС: {wm['current_page']}")
        if wm.get("shown_options"):
            lines.append("📋 ТЫ УЖЕ ПОКАЗАЛ ВАРИАНТЫ:")
            for i, opt in enumerate(wm['shown_options'][:5], 1):
                lines.append(f"   {i}. {opt}")
        if wm.get("last_action"):
            lines.append(f"⚡ ПОСЛЕДНЕЕ ДЕЙСТВИЕ: {wm['last_action']}")

        # Включаем всё из MINIMAL
        if user_info.get("location"):
            lines.append(f"\n📍 Местоположение: {user_info['location']}")

        if user_info.get("dietary_restrictions"):
            restrictions = ", ".join(user_info["dietary_restrictions"])
            lines.append(f"⚠️  Аллергии: {restrictions}")
        else:
            lines.append("⚠️  Аллергии: нет")

        # Бюджет (если есть)
        if user_info.get("budget_preferences"):
            budget_str = ", ".join(
                f"{k}: {v}₽" for k, v in user_info["budget_preferences"].items()
            )
            lines.append(f"💰 Бюджет: {budget_str}")

        # Проверенные факты (максимум 3, отфильтрованные по task_type)
        facts_lines = self._filter_verified_facts(verified, task_type, max_facts=3)
        if facts_lines:
            lines.append("\n✓ Проверенные факты:")
            lines.extend(facts_lines)

        # Обязательный язык-якорь
        lines.append("\nОтвечай на русском языке.")

        return "\n".join(lines)

    def _generate_full_context(
        self,
        user_info: Dict[str, Any],
        verified: Dict[str, Any],
        history: Dict[str, Any]
    ) -> str:
        """
        Генерация полного контекста (~1000+ токенов)
        Вся доступная информация без фильтрации + WORKING MEMORY
        """
        lines = ["📚 БАЗА ЗНАНИЙ О ПОЛЬЗОВАТЕЛЕ:"]

        # WORKING MEMORY первым делом!
        wm = self.knowledge.get("working_memory", {})
        if any([wm.get("current_task"), wm.get("current_page"), wm.get("shown_options")]):
            lines.append("\n🔥 КРАТКОСРОЧНАЯ ПАМЯТЬ (ТЕКУЩАЯ ЗАДАЧА):")
            if wm.get("current_task"):
                lines.append(f"  🎯 Задача: {wm['current_task']}")
            if wm.get("current_page"):
                lines.append(f"  📄 Страница: {wm['current_page']}")
            if wm.get("shown_options"):
                lines.append("  📋 Показанные варианты:")
                for i, opt in enumerate(wm['shown_options'], 1):
                    lines.append(f"     {i}. {opt}")
            if wm.get("last_action"):
                lines.append(f"  ⚡ Последнее действие: {wm['last_action']}")
            if wm.get("context"):
                lines.append(f"  💡 Доп. контекст: {wm['context']}")

        # User info
        if user_info.get("location"):
            lines.append(f"📍 Местоположение: {user_info['location']}")

        if user_info.get("dietary_restrictions"):
            restrictions = ", ".join(user_info["dietary_restrictions"])
            lines.append(f"🚨 Ограничения питания: {restrictions}")

        if user_info.get("budget_preferences"):
            budget_str = ", ".join(
                f"{k}: {v}₽" for k, v in user_info["budget_preferences"].items()
            )
            lines.append(f"💰 Бюджет: {budget_str}")

        # Verified facts
        if verified.get("restaurants"):
            lines.append("\n✅ ПРОВЕРЕННЫЕ РЕСТОРАНЫ:")
            for city, restaurants in verified["restaurants"].items():
                lines.append(f"  {city}: {', '.join(restaurants)}")

        if verified.get("services"):
            lines.append("\n✅ ПРОВЕРЕННЫЕ СЕРВИСЫ:")
            for category, services in verified["services"].items():
                lines.append(f"  {category}: {', '.join(services)}")

        # История
        if history.get("rejected_suggestions"):
            recent_rejected = history["rejected_suggestions"][-3:]  # последние 3
            lines.append(f"\n❌ Пользователь НЕ любит: {', '.join(recent_rejected)}")

        # Обязательный язык-якорь
        lines.append("\nОтвечай на русском языке.")

        return "\n".join(lines)

    def _filter_verified_facts(
        self,
        verified: Dict[str, Any],
        task_type: Optional[str],
        max_facts: int = 3
    ) -> List[str]:
        """
        Фильтрация проверенных фактов по типу задачи

        Args:
            verified: Проверенные факты
            task_type: Тип задачи (shopping/email/job_search/None)
            max_facts: Максимальное количество фактов

        Returns:
            Список строк с отфильтрованными фактами
        """
        fact_lines = []
        fact_count = 0

        # Для shopping - только рестораны и сервисы доставки еды
        if task_type == "shopping":
            if verified.get("restaurants") and fact_count < max_facts:
                for city, restaurants in verified["restaurants"].items():
                    if fact_count >= max_facts:
                        break
                    rest_str = ", ".join(restaurants[:2])  # Максимум 2 ресторана
                    fact_lines.append(f"  - Рестораны в {city}: {rest_str}")
                    fact_count += 1

            if verified.get("services") and fact_count < max_facts:
                food_services = {k: v for k, v in verified["services"].items()
                                if "доставка" in k.lower() or "еда" in k.lower()}
                for category, services in food_services.items():
                    if fact_count >= max_facts:
                        break
                    fact_lines.append(f"  - {category}: {', '.join(services[:2])}")
                    fact_count += 1

        # Для email - только почтовые сервисы
        elif task_type == "email":
            if verified.get("services") and fact_count < max_facts:
                email_services = {k: v for k, v in verified["services"].items()
                                 if "почта" in k.lower() or "email" in k.lower()}
                for category, services in email_services.items():
                    if fact_count >= max_facts:
                        break
                    fact_lines.append(f"  - {category}: {', '.join(services[:2])}")
                    fact_count += 1

        # Для job_search - только локации и компании
        elif task_type == "job_search":
            if verified.get("locations") and fact_count < max_facts:
                for key, locations in verified["locations"].items():
                    if fact_count >= max_facts:
                        break
                    fact_lines.append(f"  - Города для работы: {', '.join(locations[:3])}")
                    fact_count += 1

            if verified.get("companies") and fact_count < max_facts:
                for category, companies in verified["companies"].items():
                    if fact_count >= max_facts:
                        break
                    fact_lines.append(f"  - Компании: {', '.join(companies[:2])}")
                    fact_count += 1

        # Для None - берём всё (максимум max_facts)
        else:
            if verified.get("restaurants") and fact_count < max_facts:
                for city, restaurants in verified["restaurants"].items():
                    if fact_count >= max_facts:
                        break
                    rest_str = ", ".join(restaurants[:2])
                    fact_lines.append(f"  - Рестораны в {city}: {rest_str}")
                    fact_count += 1

            if verified.get("services") and fact_count < max_facts:
                for category, services in list(verified["services"].items())[:max_facts - fact_count]:
                    fact_lines.append(f"  - {category}: {', '.join(services[:2])}")
                    fact_count += 1

        return fact_lines

    def estimate_tokens(self, level: ContextLevel, task_type: Optional[str] = None) -> int:
        """
        Оценивает количество токенов для указанного уровня контекста

        Args:
            level: Уровень детализации
            task_type: Тип задачи для локализации (опционально)

        Returns:
            Примерное количество токенов
        """
        # Генерируем контекст (без логирования, чтобы избежать рекурсии)
        user_info = self.knowledge["user_info"]
        verified = self.knowledge["verified_facts"]
        history = self.knowledge["interaction_history"]

        if level == ContextLevel.MINIMAL:
            context = self._generate_minimal_context(user_info)
        elif level == ContextLevel.COMPACT:
            context = self._generate_compact_context(user_info, verified, history, task_type)
        else:  # ContextLevel.FULL
            context = self._generate_full_context(user_info, verified, history)

        # Оцениваем токены
        # Кириллица: ~2.5 символа/токен, латиница: ~4 символа/токен
        cyrillic_count = sum(1 for c in context if '\u0400' <= c <= '\u04FF')
        latin_count = len(context) - cyrillic_count

        estimated = (cyrillic_count / 2.5) + (latin_count / 4.0)
        return int(estimated)

    def check_fact_exists(self, fact_type: str, query: str) -> Optional[str]:
        """
        Проверить существует ли факт в базе знаний

        Args:
            fact_type: тип факта ("restaurant", "service", "location")
            query: что проверяем (название ресторана, сервиса и т.д.)

        Returns:
            None если факта нет, иначе детали факта
        """
        query_lower = query.lower()

        if fact_type == "restaurant":
            restaurants = self.knowledge["verified_facts"].get("restaurants", {})
            for city, names in restaurants.items():
                for name in names:
                    if query_lower in name.lower() or name.lower() in query_lower:
                        return f"Ресторан '{name}' проверен в городе {city}"

        elif fact_type == "service":
            services = self.knowledge["verified_facts"].get("services", {})
            for category, names in services.items():
                for name in names:
                    if query_lower in name.lower() or name.lower() in query_lower:
                        return f"Сервис '{name}' проверен в категории {category}"

        return None

    def should_verify_before_claiming(self, agent_response: str) -> bool:
        """
        Определить нужно ли проверить факт перед утверждением

        Анализирует ответ агента и определяет содержит ли он
        утверждения о существовании чего-либо

        Args:
            agent_response: ответ агента

        Returns:
            True если нужна проверка
        """
        response_lower = agent_response.lower()

        # Паттерны утверждений требующих проверки
        claim_patterns = [
            "ресторан", "кафе", "есть в", "находится в",
            "доступен в", "работает в", "существует",
            "это популярная", "у них есть", "можно заказать в"
        ]

        # Паттерны неуверенности (не требуют проверки)
        uncertainty_patterns = [
            "возможно", "вероятно", "наверное", "может быть",
            "я думаю", "попробую найти", "давай проверим"
        ]

        # Если есть неуверенность - проверка не нужна
        if any(pattern in response_lower for pattern in uncertainty_patterns):
            return False

        # Если есть утверждение - нужна проверка
        if any(pattern in response_lower for pattern in claim_patterns):
            return True

        return False

    def add_verified_fact(self, fact_type: str, category: str, fact: str):
        """
        Добавить проверенный факт в базу знаний

        Args:
            fact_type: тип факта ("restaurants", "services", "locations")
            category: категория (город, тип сервиса)
            fact: сам факт (название ресторана, сервиса)
        """
        if fact_type not in self.knowledge["verified_facts"]:
            self.knowledge["verified_facts"][fact_type] = {}

        if category not in self.knowledge["verified_facts"][fact_type]:
            self.knowledge["verified_facts"][fact_type][category] = []

        if fact not in self.knowledge["verified_facts"][fact_type][category]:
            self.knowledge["verified_facts"][fact_type][category].append(fact)
            self.logger.info(f"Добавлен проверенный факт: {fact_type}.{category} += {fact}")
            self.save()

    def set_working_context(
        self,
        current_task: Optional[str] = None,
        current_page: Optional[str] = None,
        shown_options: Optional[List[str]] = None,
        last_action: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Обновить краткосрочную рабочую память агента

        Args:
            current_task: Описание текущей задачи
            current_page: Где сейчас находится агент
            shown_options: Варианты, которые показал агент
            last_action: Последнее действие агента
            context: Дополнительный контекст
        """
        wm = self.knowledge.get("working_memory", {})

        if current_task is not None:
            wm["current_task"] = current_task
        if current_page is not None:
            wm["current_page"] = current_page
        if shown_options is not None:
            wm["shown_options"] = shown_options
        if last_action is not None:
            wm["last_action"] = last_action
        if context is not None:
            wm["context"].update(context)

        self.knowledge["working_memory"] = wm
        self.logger.debug(f"Working memory обновлена: task={current_task}, page={current_page}")
        self.save()

    def get_working_context(self) -> Dict[str, Any]:
        """
        Получить текущий рабочий контекст

        Returns:
            Словарь с краткосрочной памятью
        """
        return self.knowledge.get("working_memory", {})

    def clear_working_memory(self):
        """Очистить краткосрочную память (при завершении задачи)"""
        self.knowledge["working_memory"] = {
            "current_task": None,
            "current_page": None,
            "shown_options": [],
            "last_action": None,
            "context": {}
        }
        self.logger.info("Working memory очищена")
        self.save()

    def clear(self):
        """Очистить всю базу знаний"""
        self.logger.warning("База знаний очищена")
        self.knowledge = self._load_or_create()
        if self.storage_path.exists():
            self.storage_path.unlink()
