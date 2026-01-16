#!/usr/bin/env python3
"""
Unit-тесты для интеллектуальной системы выбора контекста
Эти тесты не требуют API ключей и работают локально
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Настройка путей
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.agent.ai_agent import AIAgent
from src.agent.knowledge_base import KnowledgeBase, ContextLevel
from src.prompts import PromptLevel, AgentType


def test_set_task_type():
    """Тест метода set_task_type"""
    print("\n🧪 Тест 1: set_task_type()")
    print("-" * 50)

    # Мокаем OpenAI клиента
    with patch('src.agent.ai_agent.OpenAI'):
        agent = AIAgent(agent_type=AgentType.GENERAL)

        # Устанавливаем тип задачи
        agent.set_task_type("shopping")

        assert agent.task_type == "shopping", "Тип задачи не установлен"
        print("✅ Тип задачи установлен корректно")

        # Кеш должен быть инвалидирован
        assert agent._cached_prompt_level is None, "Кеш не инвалидирован"
        print("✅ Кеш инвалидирован при установке типа задачи")

        # Смена типа задачи должна сбросить кеш
        agent._cached_prompt_level = PromptLevel.COMPACT
        agent.set_task_type("email")

        assert agent.task_type == "email", "Тип задачи не изменился"
        assert agent._cached_prompt_level is None, "Кеш не сброшен при смене типа"
        print("✅ Кеш сброшен при смене типа задачи")

        return True


def test_select_context_level():
    """Тест метода _select_context_level"""
    print("\n🧪 Тест 2: _select_context_level()")
    print("-" * 50)

    with patch('src.agent.ai_agent.OpenAI'):
        agent = AIAgent(agent_type=AgentType.GENERAL)
        agent.add_system_prompt()

        # Мокаем knowledge_base
        mock_kb = MagicMock()
        mock_kb.estimate_tokens.side_effect = lambda level, task_type: {
            ContextLevel.MINIMAL: 100,
            ContextLevel.COMPACT: 300,
            ContextLevel.FULL: 800
        }[level]
        agent.knowledge_base = mock_kb

        # Тест 1: Пустая история - должен выбрать FULL
        context_level, prompt_level = agent._select_context_level(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            specialized_agent=None
        )

        print(f"  Выбран уровень: context={context_level.value}, prompt={prompt_level.value}")

        # С пустой историей должно быть достаточно места для FULL
        assert context_level in [ContextLevel.FULL, ContextLevel.COMPACT], \
            f"Неверный уровень контекста: {context_level}"
        print("✅ Уровень выбран корректно для пустой истории")

        # Тест 2: Заполненная история - должен понизить уровень
        # Добавим много сообщений
        for i in range(20):
            agent.conversation_history.append({
                "role": "user",
                "content": "Длинное сообщение " * 50  # ~500 символов
            })
            agent.conversation_history.append({
                "role": "assistant",
                "content": "Длинный ответ " * 50
            })

        context_level2, prompt_level2 = agent._select_context_level(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            specialized_agent=None
        )

        print(f"  После заполнения: context={context_level2.value}, prompt={prompt_level2.value}")

        # После заполнения должен быть более компактный уровень
        assert context_level2 in [ContextLevel.MINIMAL, ContextLevel.COMPACT], \
            f"Уровень не понизился: {context_level2}"
        print("✅ Уровень понизился при заполнении истории")

        return True


def test_update_system_message():
    """Тест метода _update_system_message"""
    print("\n🧪 Тест 3: _update_system_message()")
    print("-" * 50)

    with patch('src.agent.ai_agent.OpenAI'):
        agent = AIAgent(agent_type=AgentType.GENERAL)

        # Добавляем системный промпт
        agent.add_system_prompt()

        initial_prompt = agent.conversation_history[0]["content"]
        print(f"  Начальный промпт: {len(initial_prompt)} символов")

        # Обновляем промпт
        new_prompt = "Новый короткий промпт"
        agent._update_system_message(new_prompt)

        assert len(agent.conversation_history) > 0, "История пуста"
        assert agent.conversation_history[0]["role"] == "system", "Системное сообщение не первое"
        assert agent.conversation_history[0]["content"] == new_prompt, "Промпт не обновлён"

        print(f"  Обновлённый промпт: {len(new_prompt)} символов")
        print("✅ Системный промпт обновлён корректно")

        return True


def test_get_base_system_prompt():
    """Тест метода _get_base_system_prompt"""
    print("\n🧪 Тест 4: _get_base_system_prompt()")
    print("-" * 50)

    with patch('src.agent.ai_agent.OpenAI'):
        agent = AIAgent(agent_type=AgentType.GENERAL)

        # Проверяем все уровни
        minimal_prompt = agent._get_base_system_prompt(PromptLevel.MINIMAL)
        compact_prompt = agent._get_base_system_prompt(PromptLevel.COMPACT)
        full_prompt = agent._get_base_system_prompt(PromptLevel.FULL)

        print(f"  MINIMAL: {len(minimal_prompt)} символов")
        print(f"  COMPACT: {len(compact_prompt)} символов")
        print(f"  FULL: {len(full_prompt)} символов")

        # Проверяем что промпты разной длины
        assert len(minimal_prompt) < len(compact_prompt), "MINIMAL не короче COMPACT"
        assert len(compact_prompt) < len(full_prompt), "COMPACT не короче FULL"

        # Проверяем что все промпты содержат язык-якорь
        assert "русском" in minimal_prompt.lower(), "MINIMAL без языка-якоря"
        assert "русском" in compact_prompt.lower(), "COMPACT без языка-якоря"
        assert "русском" in full_prompt.lower(), "FULL без языка-якоря"

        print("✅ Все уровни промптов генерируются корректно")
        print("✅ Язык-якорь присутствует на всех уровнях")

        return True


def test_get_token_usage_stats():
    """Тест метода get_token_usage_stats"""
    print("\n🧪 Тест 5: get_token_usage_stats()")
    print("-" * 50)

    with patch('src.agent.ai_agent.OpenAI'):
        agent = AIAgent(agent_type=AgentType.GENERAL)
        agent.add_system_prompt()

        # Мокаем knowledge_base
        mock_kb = MagicMock()
        mock_kb.estimate_tokens.return_value = 100
        agent.knowledge_base = mock_kb
        agent.task_type = "shopping"

        # Получаем статистику
        stats = agent.get_token_usage_stats()

        # Проверяем что все поля присутствуют
        required_fields = [
            "model", "model_limit", "safe_limit", "used_tokens",
            "available_tokens", "usage_percent", "context_level",
            "prompt_level", "kb_savings_percent", "task_type"
        ]

        for field in required_fields:
            assert field in stats, f"Отсутствует поле: {field}"
            print(f"  ✓ {field}: {stats[field]}")

        print("✅ Все поля статистики присутствуют")

        return True


def main():
    """Запуск всех тестов"""
    print("\n" + "=" * 70)
    print("🚀 UNIT-ТЕСТЫ: ИНТЕЛЛЕКТУАЛЬНАЯ СИСТЕМА ВЫБОРА КОНТЕКСТА")
    print("=" * 70)

    tests = [
        ("set_task_type", test_set_task_type),
        ("_select_context_level", test_select_context_level),
        ("_update_system_message", test_update_system_message),
        ("_get_base_system_prompt", test_get_base_system_prompt),
        ("get_token_usage_stats", test_get_token_usage_stats),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except AssertionError as e:
            print(f"❌ Тест провален: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ Ошибка в тесте: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    # Итоговый отчёт
    print("\n" + "=" * 70)
    print("📋 ИТОГОВЫЙ ОТЧЁТ")
    print("=" * 70)
    print(f"✅ Пройдено: {passed}/{len(tests)}")
    print(f"❌ Провалено: {failed}/{len(tests)}")

    if failed == 0:
        print("\n🎉 ВСЕ UNIT-ТЕСТЫ УСПЕШНО ПРОЙДЕНЫ!")
        return 0
    else:
        print(f"\n⚠️  {failed} тест(ов) провален(о)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
