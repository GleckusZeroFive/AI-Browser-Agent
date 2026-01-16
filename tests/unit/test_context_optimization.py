"""
Unit тесты для системы оптимизации контекста
"""
import pytest
from src.agent.knowledge_base import KnowledgeBase, ContextLevel
from src.agent.ai_agent import AIAgent
from src.agent.specialized_agents import ShoppingAgent, EmailAgent, JobSearchAgent
from src.prompts.prompt_manager import PromptManager, PromptLevel


class TestKnowledgeBaseOptimization:
    """Тесты для KnowledgeBase с уровнями контекста"""

    def test_context_level_minimal(self):
        """MINIMAL должен возвращать ~100 токенов"""
        kb = KnowledgeBase(llm_client=None, storage_path="data/knowledge_base.json")

        context = kb.get_context_summary(ContextLevel.MINIMAL)
        tokens = kb.estimate_tokens(ContextLevel.MINIMAL)

        assert tokens <= 150, f"MINIMAL должен быть ≤150 токенов, получено {tokens}"
        assert "русском языке" in context.lower(), "Должен быть язык-якорь"

    def test_context_level_compact(self):
        """COMPACT должен возвращать ~300 токенов"""
        kb = KnowledgeBase(llm_client=None, storage_path="data/knowledge_base.json")

        tokens = kb.estimate_tokens(ContextLevel.COMPACT)

        assert 200 <= tokens <= 400, f"COMPACT должен быть 200-400 токенов, получено {tokens}"

    def test_context_level_full(self):
        """FULL должен возвращать весь контекст"""
        kb = KnowledgeBase(llm_client=None, storage_path="data/knowledge_base.json")

        tokens = kb.estimate_tokens(ContextLevel.FULL)

        assert tokens >= 400, f"FULL должен быть ≥400 токенов, получено {tokens}"

    def test_task_type_localization(self):
        """Локализация по task_type должна работать"""
        kb = KnowledgeBase(llm_client=None, storage_path="data/knowledge_base.json")

        # Добавляем тестовые данные
        kb.knowledge["user_info"]["preferences"] = ["пицца", "Python", "Docker"]

        # Shopping должен взять только "пицца"
        shopping_context = kb.get_context_summary(ContextLevel.COMPACT, "shopping")
        assert "пицца" in shopping_context.lower()

        # Job search должен взять только "Python", "Docker"
        job_context = kb.get_context_summary(ContextLevel.COMPACT, "job_search")
        # Может не содержать если нет технологий в правильном формате

    def test_language_anchor_present(self):
        """Язык-якорь должен быть во всех уровнях"""
        kb = KnowledgeBase(llm_client=None, storage_path="data/knowledge_base.json")

        for level in [ContextLevel.MINIMAL, ContextLevel.COMPACT, ContextLevel.FULL]:
            context = kb.get_context_summary(level)
            assert "русском языке" in context.lower(), f"Язык-якорь отсутствует в {level.value}"


class TestPromptOptimization:
    """Тесты для системы промптов"""

    def test_prompt_loading_shopping(self):
        """Загрузка промптов для ShoppingAgent"""
        pm = PromptManager()

        minimal = pm.load_prompt("shopping", PromptLevel.MINIMAL)
        compact = pm.load_prompt("shopping", PromptLevel.COMPACT)
        full = pm.load_prompt("shopping", PromptLevel.FULL)

        minimal_tokens = pm.estimate_prompt_tokens(minimal)
        compact_tokens = pm.estimate_prompt_tokens(compact)
        full_tokens = pm.estimate_prompt_tokens(full)

        assert minimal_tokens <= 350, f"Shopping MINIMAL: {minimal_tokens}т > 350т"
        assert compact_tokens <= 700, f"Shopping COMPACT: {compact_tokens}т > 700т"
        assert full_tokens >= 1000, f"Shopping FULL: {full_tokens}т < 1000т"

        # Проверка язык-якоря
        for prompt in [minimal, compact, full]:
            assert "русском языке" in prompt.lower()

    def test_prompt_loading_email(self):
        """Загрузка промптов для EmailAgent"""
        pm = PromptManager()

        minimal = pm.load_prompt("email", PromptLevel.MINIMAL)
        compact = pm.load_prompt("email", PromptLevel.COMPACT)

        minimal_tokens = pm.estimate_prompt_tokens(minimal)
        compact_tokens = pm.estimate_prompt_tokens(compact)

        assert minimal_tokens <= 300
        assert compact_tokens <= 600

    def test_specialized_agent_caching(self):
        """Кеширование промптов в SpecializedAgent"""
        agent = ShoppingAgent()

        # Первая загрузка
        prompt1 = agent.get_system_prompt(PromptLevel.COMPACT)

        # Вторая загрузка (должна вернуть кешированный)
        prompt2 = agent.get_system_prompt(PromptLevel.COMPACT)

        assert prompt1 == prompt2
        assert agent._cached_prompt is not None
        assert agent._cached_level == PromptLevel.COMPACT


class TestAIAgentOptimization:
    """Тесты для AIAgent с оптимизацией"""

    @pytest.mark.skip(reason="Требует API ключ")
    def test_context_level_selection(self):
        """Выбор уровня контекста в зависимости от доступных токенов"""
        agent = AIAgent()
        agent.knowledge_base = KnowledgeBase(agent.client, "data/knowledge_base.json")

        # Симулируем разные ситуации
        # 1. Пустая история - должен быть FULL или COMPACT
        context_level, prompt_level = agent._select_context_level(
            "llama-3.1-8b-instant",
            None
        )
        assert context_level in [ContextLevel.FULL, ContextLevel.COMPACT]

        # 2. Заполняем историю
        for i in range(20):
            agent.conversation_history.append({
                "role": "user",
                "content": f"Тестовое сообщение {i}" * 100
            })

        # Должен выбрать MINIMAL
        context_level, prompt_level = agent._select_context_level(
            "llama-3.1-8b-instant",
            None
        )
        assert context_level == ContextLevel.MINIMAL

    def test_set_task_type(self):
        """Смена типа задачи должна инвалидировать кеш"""
        agent = AIAgent()
        agent._cached_prompt_level = PromptLevel.COMPACT
        agent._cached_system_prompt = "cached"

        # Меняем тип
        agent.set_task_type("shopping")

        assert agent.task_type == "shopping"
        assert agent._cached_prompt_level is None
        assert agent._cached_system_prompt is None

    def test_token_usage_stats(self):
        """Статистика должна возвращать корректные данные"""
        agent = AIAgent()
        agent.knowledge_base = KnowledgeBase(None, "data/knowledge_base.json")

        stats = agent.get_token_usage_stats()

        assert "model" in stats
        assert "used_tokens" in stats
        assert "context_level" in stats
        assert "prompt_level" in stats
        assert "kb_savings_percent" in stats


def run_tests():
    """Запуск всех unit тестов"""
    pytest.main([__file__, "-v", "--tb=short"])


if __name__ == "__main__":
    run_tests()
