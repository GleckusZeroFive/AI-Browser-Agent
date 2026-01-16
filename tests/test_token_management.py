#!/usr/bin/env python3
"""
Тест для проверки управления токенами и контекстом
"""
import sys
import os

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.agent.ai_agent import AIAgent
from src.config import Config

def test_token_estimation():
    """Тест оценки токенов"""
    print("=" * 70)
    print("ТЕСТ 1: Оценка количества токенов")
    print("=" * 70)

    agent = AIAgent()

    # Тест с английским текстом
    english_text = "Hello, this is a test message for token estimation."
    tokens_en = agent._estimate_tokens(english_text)
    print(f"\nАнглийский текст ({len(english_text)} символов): {tokens_en} токенов")
    print(f"Текст: {english_text}")

    # Тест с русским текстом
    russian_text = "Привет, это тестовое сообщение для оценки токенов."
    tokens_ru = agent._estimate_tokens(russian_text)
    print(f"\nРусский текст ({len(russian_text)} символов): {tokens_ru} токенов")
    print(f"Текст: {russian_text}")

    # Тест с большим текстом
    long_text = "Это длинное сообщение. " * 100
    tokens_long = agent._estimate_tokens(long_text)
    print(f"\nДлинный текст ({len(long_text)} символов): {tokens_long} токенов")

    print("\n✅ Тест оценки токенов завершен\n")


def test_context_calculation():
    """Тест подсчета токенов в контексте"""
    print("=" * 70)
    print("ТЕСТ 2: Подсчет токенов в контексте разговора")
    print("=" * 70)

    agent = AIAgent()
    agent.add_system_prompt()

    # Добавляем несколько сообщений
    agent.conversation_history.append({"role": "user", "content": "Привет, как дела?"})
    agent.conversation_history.append({"role": "assistant", "content": "Привет! Всё отлично, чем могу помочь?"})
    agent.conversation_history.append({"role": "user", "content": "Найди мне пиццу"})

    total_tokens = agent._calculate_context_tokens()
    print(f"\nВсего сообщений: {len(agent.conversation_history)}")
    print(f"Общее количество токенов: {total_tokens}")

    # Показываем детали
    for i, msg in enumerate(agent.conversation_history):
        content = msg.get("content", "")
        tokens = agent._estimate_tokens(content)
        role = msg.get("role", "unknown")
        preview = content[:50] + "..." if len(content) > 50 else content
        print(f"  [{i}] {role}: {tokens} токенов - {preview}")

    print("\n✅ Тест подсчета контекста завершен\n")


def test_model_selection():
    """Тест выбора модели с учетом размера контекста"""
    print("=" * 70)
    print("ТЕСТ 3: Выбор подходящей модели")
    print("=" * 70)

    agent = AIAgent()

    # Тест 1: Маленький контекст
    small_tokens = 1000
    model = agent._get_suitable_fallback_model(small_tokens)
    print(f"\nКонтекст: {small_tokens} токенов")
    print(f"Выбранная модель: {model}")
    if model:
        limit = Config.MODEL_TOKEN_LIMITS.get(model, 6000)
        print(f"Лимит модели: {limit} токенов")

    # Тест 2: Средний контекст
    medium_tokens = 5000
    model = agent._get_suitable_fallback_model(medium_tokens)
    print(f"\nКонтекст: {medium_tokens} токенов")
    print(f"Выбранная модель: {model}")
    if model:
        limit = Config.MODEL_TOKEN_LIMITS.get(model, 6000)
        print(f"Лимит модели: {limit} токенов")

    # Тест 3: Большой контекст
    large_tokens = 8000
    model = agent._get_suitable_fallback_model(large_tokens)
    print(f"\nКонтекст: {large_tokens} токенов")
    print(f"Выбранная модель: {model}")
    if model:
        limit = Config.MODEL_TOKEN_LIMITS.get(model, 6000)
        print(f"Лимит модели: {limit} токенов")

    # Тест 4: Очень большой контекст
    huge_tokens = 20000
    model = agent._get_suitable_fallback_model(huge_tokens)
    print(f"\nКонтекст: {huge_tokens} токенов")
    print(f"Выбранная модель: {model}")
    if model:
        limit = Config.MODEL_TOKEN_LIMITS.get(model, 6000)
        print(f"Лимит модели: {limit} токенов")
    else:
        print("⚠️ Нет подходящей модели - потребуется сокращение контекста")

    print("\n✅ Тест выбора модели завершен\n")


def test_context_trimming():
    """Тест сокращения контекста"""
    print("=" * 70)
    print("ТЕСТ 4: Сокращение контекста при превышении лимита")
    print("=" * 70)

    agent = AIAgent()
    agent.add_system_prompt()

    # Добавляем много сообщений
    for i in range(30):
        agent.conversation_history.append({
            "role": "user",
            "content": f"Тестовое сообщение номер {i} с некоторым текстом для увеличения размера"
        })
        agent.conversation_history.append({
            "role": "assistant",
            "content": f"Ответ на сообщение {i} с дополнительной информацией и деталями"
        })

    tokens_before = agent._calculate_context_tokens()
    messages_before = len(agent.conversation_history)

    print(f"\nДо сокращения:")
    print(f"  Сообщений: {messages_before}")
    print(f"  Токенов: {tokens_before}")

    # Сокращаем контекст
    max_tokens = 2000
    agent._trim_conversation_history(max_tokens)

    tokens_after = agent._calculate_context_tokens()
    messages_after = len(agent.conversation_history)

    print(f"\nПосле сокращения (лимит: {max_tokens} токенов):")
    print(f"  Сообщений: {messages_after}")
    print(f"  Токенов: {tokens_after}")

    # Проверяем что системный промпт сохранен
    if agent.conversation_history and agent.conversation_history[0].get("role") == "system":
        print(f"\n✅ Системный промпт сохранен")
    else:
        print(f"\n❌ Системный промпт потерян!")

    print(f"\nСокращение: {messages_before - messages_after} сообщений удалено")
    print(f"Экономия: {tokens_before - tokens_after} токенов")

    print("\n✅ Тест сокращения контекста завершен\n")


def main():
    """Запуск всех тестов"""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "ТЕСТИРОВАНИЕ УПРАВЛЕНИЯ ТОКЕНАМИ" + " " * 21 + "║")
    print("╚" + "=" * 68 + "╝")
    print()

    try:
        test_token_estimation()
        test_context_calculation()
        test_model_selection()
        test_context_trimming()

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
