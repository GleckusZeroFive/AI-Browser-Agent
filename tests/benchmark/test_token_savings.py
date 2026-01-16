"""
Benchmark тесты: измерение экономии токенов в реальных сценариях
"""
import pytest
import sys
from pathlib import Path

# Добавляем корневую директорию в PYTHONPATH
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agent.knowledge_base import KnowledgeBase, ContextLevel
from src.agent.specialized_agents import ShoppingAgent, EmailAgent, JobSearchAgent
from src.prompts.prompt_manager import PromptManager, PromptLevel


class TestTokenSavingsBenchmark:
    """Benchmark тесты для измерения экономии"""

    def test_shopping_agent_savings(self):
        """Измерение экономии для ShoppingAgent"""
        kb = KnowledgeBase(None, "data/knowledge_base.json")
        agent = ShoppingAgent()

        # KB токены
        kb_minimal = kb.estimate_tokens(ContextLevel.MINIMAL, "shopping")
        kb_compact = kb.estimate_tokens(ContextLevel.COMPACT, "shopping")
        kb_full = kb.estimate_tokens(ContextLevel.FULL, "shopping")

        # Промпт токены
        prompt_minimal = agent.get_system_prompt(PromptLevel.MINIMAL)
        prompt_compact = agent.get_system_prompt(PromptLevel.COMPACT)
        prompt_full = agent.get_system_prompt(PromptLevel.FULL)

        pm = PromptManager()

        p_minimal = pm.estimate_prompt_tokens(prompt_minimal)
        p_compact = pm.estimate_prompt_tokens(prompt_compact)
        p_full = pm.estimate_prompt_tokens(prompt_full)

        # Общие токены
        total_minimal = kb_minimal + p_minimal
        total_compact = kb_compact + p_compact
        total_full = kb_full + p_full

        # Экономия
        savings_minimal = ((total_full - total_minimal) / total_full * 100) if total_full > 0 else 0
        savings_compact = ((total_full - total_compact) / total_full * 100) if total_full > 0 else 0

        print("\n" + "="*60)
        print("📊 SHOPPING AGENT - ЭКОНОМИЯ ТОКЕНОВ")
        print("="*60)
        print(f"MINIMAL: {total_minimal}т (экономия {savings_minimal:.1f}%)")
        print(f"  KB: {kb_minimal}т + Prompt: {p_minimal}т")
        print(f"COMPACT: {total_compact}т (экономия {savings_compact:.1f}%)")
        print(f"  KB: {kb_compact}т + Prompt: {p_compact}т")
        print(f"FULL:    {total_full}т (базовый)")
        print(f"  KB: {kb_full}т + Prompt: {p_full}т")
        print("="*60)

        # Проверяем что экономия достигается
        assert savings_minimal >= 40, f"MINIMAL экономия <40%: {savings_minimal:.1f}%"
        assert savings_compact >= 20, f"COMPACT экономия <20%: {savings_compact:.1f}%"

    def test_email_agent_savings(self):
        """Измерение экономии для EmailAgent"""
        kb = KnowledgeBase(None, "data/knowledge_base.json")
        agent = EmailAgent()
        pm = PromptManager()

        # KB токены
        kb_minimal = kb.estimate_tokens(ContextLevel.MINIMAL, "email")
        kb_full = kb.estimate_tokens(ContextLevel.FULL, "email")

        # Промпт токены
        p_minimal = pm.estimate_prompt_tokens(agent.get_system_prompt(PromptLevel.MINIMAL))
        p_full = pm.estimate_prompt_tokens(agent.get_system_prompt(PromptLevel.FULL))

        # Общие токены
        total_minimal = kb_minimal + p_minimal
        total_full = kb_full + p_full

        # Экономия
        savings = ((total_full - total_minimal) / total_full * 100) if total_full > 0 else 0

        print("\n" + "="*60)
        print("📊 EMAIL AGENT - ЭКОНОМИЯ ТОКЕНОВ")
        print("="*60)
        print(f"MINIMAL: {total_minimal}т (экономия {savings:.1f}%)")
        print(f"FULL:    {total_full}т")
        print("="*60)

        assert savings >= 35, f"Email MINIMAL экономия <35%: {savings:.1f}%"

    def test_all_agents_comparison(self):
        """Сравнение экономии для всех агентов"""
        kb = KnowledgeBase(None, "data/knowledge_base.json")

        agents = {
            "Shopping": (ShoppingAgent(), "shopping"),
            "Email": (EmailAgent(), "email"),
            "JobSearch": (JobSearchAgent(), "job_search")
        }

        pm = PromptManager()

        print("\n" + "="*60)
        print("📊 СРАВНЕНИЕ ЭКОНОМИИ ПО АГЕНТАМ")
        print("="*60)

        results = []
        for name, (agent, task_type) in agents.items():
            kb_minimal = kb.estimate_tokens(ContextLevel.MINIMAL, task_type)
            kb_full = kb.estimate_tokens(ContextLevel.FULL, task_type)

            p_minimal_txt = agent.get_system_prompt(PromptLevel.MINIMAL)
            p_full_txt = agent.get_system_prompt(PromptLevel.FULL)

            p_minimal = pm.estimate_prompt_tokens(p_minimal_txt)
            p_full = pm.estimate_prompt_tokens(p_full_txt)

            total_minimal = kb_minimal + p_minimal
            total_full = kb_full + p_full

            savings = ((total_full - total_minimal) / total_full * 100) if total_full > 0 else 0

            print(f"{name:12} | MINIMAL: {total_minimal:4}т | FULL: {total_full:4}т | Экономия: {savings:5.1f}%")
            results.append((name, savings))

        print("="*60)

        # Проверяем минимальную экономию для каждого агента
        for name, savings in results:
            if name == "Shopping":
                assert savings >= 40, f"{name}: экономия {savings:.1f}% < 40%"
            else:
                assert savings >= 35, f"{name}: экономия {savings:.1f}% < 35%"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
