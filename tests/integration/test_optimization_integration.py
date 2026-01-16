"""
Интеграционные тесты: проверка работы всей системы оптимизации
"""
import pytest
import sys
from pathlib import Path

# Добавляем корневую директорию в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agent.ai_agent import AIAgent
from src.agent.knowledge_base import KnowledgeBase, ContextLevel
from src.agent.specialized_agents import ShoppingAgent
from src.prompts.prompt_manager import PromptLevel


class TestOptimizationIntegration:
    """Интеграционные тесты всей системы"""

    def test_full_optimization_flow(self):
        """Тест полного флоу оптимизации"""
        # 1. Создаём агента
        agent = AIAgent()
        kb = KnowledgeBase(agent.client, "data/knowledge_base.json")
        agent.knowledge_base = kb

        # 2. Устанавливаем тип задачи
        agent.set_task_type("shopping")

        # 3. Получаем статистику (начальное состояние)
        stats_initial = agent.get_token_usage_stats()

        assert stats_initial['task_type'] == 'shopping'
        assert stats_initial['context_level'] in ['minimal', 'compact', 'full']
        assert stats_initial['prompt_level'] in ['minimal', 'compact', 'full']

        print(f"✅ Начальное состояние:")
        print(f"   Контекст: {stats_initial['context_level']}")
        print(f"   Промпт: {stats_initial['prompt_level']}")
        print(f"   Использовано: {stats_initial['used_tokens']} токенов")

        # 4. Проверяем что экономия работает
        full_kb = kb.estimate_tokens(ContextLevel.FULL, "shopping")
        current_kb = kb.estimate_tokens(
            ContextLevel[stats_initial['context_level'].upper()],
            "shopping"
        )

        savings_percent = ((full_kb - current_kb) / full_kb * 100) if full_kb > 0 else 0

        print(f"   Экономия KB: {savings_percent:.1f}%")
        assert savings_percent >= 0, "Экономия не может быть отрицательной"

    def test_task_type_switch(self):
        """Тест смены типа задачи"""
        agent = AIAgent()
        kb = KnowledgeBase(agent.client, "data/knowledge_base.json")
        agent.knowledge_base = kb

        # Shopping
        agent.set_task_type("shopping")
        stats1 = agent.get_token_usage_stats()
        assert stats1['task_type'] == 'shopping'

        # Email
        agent.set_task_type("email")
        stats2 = agent.get_token_usage_stats()
        assert stats2['task_type'] == 'email'

        # Job Search
        agent.set_task_type("job_search")
        stats3 = agent.get_token_usage_stats()
        assert stats3['task_type'] == 'job_search'

        print("✅ Смена типа задачи работает корректно")

    def test_savings_calculation(self):
        """Проверка расчёта экономии токенов"""
        agent = AIAgent()
        kb = KnowledgeBase(agent.client, "data/knowledge_base.json")
        agent.knowledge_base = kb

        # Сравниваем разные уровни
        minimal_tokens = kb.estimate_tokens(ContextLevel.MINIMAL)
        full_tokens = kb.estimate_tokens(ContextLevel.FULL)

        savings = ((full_tokens - minimal_tokens) / full_tokens) * 100 if full_tokens > 0 else 0

        print(f"✅ Экономия MINIMAL vs FULL: {savings:.1f}%")
        print(f"   MINIMAL: {minimal_tokens}т")
        print(f"   FULL: {full_tokens}т")

        # Экономия должна быть хотя бы 30%
        assert savings >= 30, f"Ожидалась экономия ≥30%, получено {savings:.1f}%"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
