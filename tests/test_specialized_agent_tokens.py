#!/usr/bin/env python3
"""
Тест для проверки работы специализированных агентов с новой системой управления токенами
"""
import sys
import os

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.agent.ai_agent import AIAgent
from src.agent.specialized_agents import ShoppingAgent, EmailAgent, JobSearchAgent
from src.config import Config

def test_specialized_agent_prompts():
    """Тест размеров промптов специализированных агентов"""
    print("=" * 70)
    print("ТЕСТ: Размеры промптов специализированных агентов")
    print("=" * 70)

    agents = [
        ("ShoppingAgent", ShoppingAgent()),
        ("EmailAgent", EmailAgent()),
        ("JobSearchAgent", JobSearchAgent()),
    ]

    ai_agent = AIAgent()

    for name, agent in agents:
        prompt = agent.get_system_prompt()
        tokens = ai_agent._estimate_tokens(prompt)
        model = agent.get_model()
        model_limit = Config.MODEL_TOKEN_LIMITS.get(model, 6000)
        safe_limit = int(model_limit * Config.SAFE_TOKEN_MARGIN)

        print(f"\n{name}:")
        print(f"  Модель: {model}")
        print(f"  Лимит модели: {model_limit:,} TPM")
        print(f"  Безопасный лимит (70%): {safe_limit:,} токенов")
        print(f"  Размер промпта: {tokens:,} токенов")
        print(f"  % от лимита модели: {tokens/model_limit*100:.1f}%")
        print(f"  % от безопасного лимита: {tokens/safe_limit*100:.1f}%")

        if tokens > safe_limit:
            print(f"  ⚠️  ПРЕДУПРЕЖДЕНИЕ: Промпт превышает безопасный лимит!")
        else:
            print(f"  ✅ OK: Промпт в пределах безопасного лимита")

    print("\n✅ Тест размеров промптов завершен\n")


def test_fallback_model_selection():
    """Тест выбора fallback-модели для больших промптов"""
    print("=" * 70)
    print("ТЕСТ: Выбор fallback-модели для специализированных агентов")
    print("=" * 70)

    # Симулируем сценарий с ShoppingAgent
    shopping_agent = ShoppingAgent()
    ai_agent = AIAgent()

    prompt = shopping_agent.get_system_prompt()
    prompt_tokens = ai_agent._estimate_tokens(prompt)

    print(f"\nShoppingAgent промпт: {prompt_tokens:,} токенов")
    print(f"\nПроверяем какая модель будет выбрана при разных лимитах:\n")

    # Тест 1: Промпт + небольшая история (3000 токенов)
    context_tokens = prompt_tokens + 3000
    print(f"Сценарий 1: Промпт + история = {context_tokens:,} токенов")
    suitable_model = ai_agent._get_suitable_fallback_model(context_tokens)
    if suitable_model:
        limit = Config.MODEL_TOKEN_LIMITS.get(suitable_model, 6000)
        print(f"  ✅ Выбрана модель: {suitable_model} (лимит {limit:,} TPM)")
    else:
        print(f"  ❌ Подходящая модель не найдена - нужно сокращение контекста")

    # Тест 2: Промпт + большая история (5000 токенов)
    context_tokens = prompt_tokens + 5000
    print(f"\nСценарий 2: Промпт + история = {context_tokens:,} токенов")
    suitable_model = ai_agent._get_suitable_fallback_model(context_tokens)
    if suitable_model:
        limit = Config.MODEL_TOKEN_LIMITS.get(suitable_model, 6000)
        print(f"  ✅ Выбрана модель: {suitable_model} (лимит {limit:,} TPM)")
    else:
        print(f"  ❌ Подходящая модель не найдена - нужно сокращение контекста")

    # Тест 3: Проверка порядка fallback-моделей
    print(f"\nПорядок fallback-моделей (от большего лимита к меньшему):")
    for i, model in enumerate(Config.FALLBACK_MODELS, 1):
        limit = Config.MODEL_TOKEN_LIMITS.get(model, 6000)
        print(f"  {i}. {model}: {limit:,} TPM")

    print("\n✅ Тест выбора fallback-модели завершен\n")


def test_context_with_specialized_agent():
    """Тест управления контекстом со специализированным агентом"""
    print("=" * 70)
    print("ТЕСТ: Управление контекстом со специализированным агентом")
    print("=" * 70)

    # Создаем AI агента со специализированным промптом
    ai_agent = AIAgent()
    shopping_agent = ShoppingAgent()

    # Добавляем промпт
    system_prompt = shopping_agent.get_system_prompt()
    ai_agent.conversation_history.append({
        "role": "system",
        "content": system_prompt
    })

    # Симулируем диалог
    for i in range(10):
        ai_agent.conversation_history.append({
            "role": "user",
            "content": f"Тестовое сообщение пользователя #{i} с некоторым текстом"
        })
        ai_agent.conversation_history.append({
            "role": "assistant",
            "content": f"Ответ агента на сообщение #{i} с дополнительной информацией"
        })

    tokens_before = ai_agent._calculate_context_tokens()
    messages_before = len(ai_agent.conversation_history)

    print(f"\nДо проверки лимита:")
    print(f"  Сообщений: {messages_before}")
    print(f"  Токенов: {tokens_before:,}")

    # Проверяем лимиты разных моделей
    print(f"\nПроверка соответствия лимитам моделей:")

    for model_name, limit in Config.MODEL_TOKEN_LIMITS.items():
        safe_limit = int(limit * Config.SAFE_TOKEN_MARGIN)
        fits = tokens_before <= safe_limit
        status = "✅ Влезает" if fits else "❌ Превышен"
        print(f"  {model_name}: {limit:,} TPM (safe: {safe_limit:,}) - {status}")

    # Тестируем сокращение для модели с маленьким лимитом
    print(f"\nСимуляция переключения на модель с маленьким лимитом (6000 TPM):")
    safe_limit_maverick = int(6000 * Config.SAFE_TOKEN_MARGIN)

    if tokens_before > safe_limit_maverick:
        print(f"  Контекст ({tokens_before:,}) превышает лимит ({safe_limit_maverick:,})")
        print(f"  Сокращаем контекст...")
        ai_agent._trim_conversation_history(safe_limit_maverick)

        tokens_after = ai_agent._calculate_context_tokens()
        messages_after = len(ai_agent.conversation_history)

        print(f"\nПосле сокращения:")
        print(f"  Сообщений: {messages_after}")
        print(f"  Токенов: {tokens_after:,}")
        print(f"  Сокращено: {messages_before - messages_after} сообщений")
        print(f"  Экономия: {tokens_before - tokens_after:,} токенов")

        # Проверяем что промпт сохранен
        if ai_agent.conversation_history and ai_agent.conversation_history[0].get("role") == "system":
            print(f"  ✅ Системный промпт сохранен")
        else:
            print(f"  ❌ Системный промпт потерян!")

    print("\n✅ Тест управления контекстом завершен\n")


def main():
    """Запуск всех тестов"""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 10 + "ТЕСТИРОВАНИЕ СПЕЦИАЛИЗИРОВАННЫХ АГЕНТОВ" + " " * 18 + "║")
    print("╚" + "=" * 68 + "╝")
    print()

    try:
        test_specialized_agent_prompts()
        test_fallback_model_selection()
        test_context_with_specialized_agent()

        print("=" * 70)
        print("✅ ВСЕ ТЕСТЫ УСПЕШНО ЗАВЕРШЕНЫ")
        print("=" * 70)
        print()

    except Exception as e:
        print(f"\n❌ ОШИБКА ПРИ ВЫПОЛНЕНИИ ТЕСТОВ: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
