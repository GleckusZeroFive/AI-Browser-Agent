#!/usr/bin/env python3
"""
Тестовый скрипт для проверки исправлений галлюцинаций агента
"""
import json
from src.agent.ai_agent import AIAgent

def test_parse_action():
    """Тестирует парсинг действий из ответов агента"""
    agent = AIAgent()

    print("=" * 70)
    print("ТЕСТ ПАРСИНГА ДЕЙСТВИЙ")
    print("=" * 70)

    # Тест 1: Правильный формат (одно действие)
    print("\n1. Правильный формат (одно действие):")
    response1 = """Открываю Додопиццу для Красноярска.
{"action": "navigate", "params": {"url": "https://dodopizza.ru/krasnoyarsk"}, "reasoning": "Переход на сайт"}"""

    action1 = agent.parse_action(response1)
    if action1:
        print(f"✅ Найдено действие: {action1['action']}")
        print(f"   Параметры: {action1['params']}")
    else:
        print("❌ Действие не найдено")

    # Тест 2: Множественные действия (галлюцинация)
    print("\n2. Множественные действия (должно взять первое):")
    response2 = """Открываю Додопиццу.
{"action": "navigate", "params": {"url": "https://dodopizza.ru/krasnoyarsk"}, "reasoning": "Переход"}

Ищу пиццу.
{"action": "search_and_type", "params": {"text": "Маргарита"}, "reasoning": "Поиск"}

Результат: Нашёл 3 варианта..."""

    action2 = agent.parse_action(response2)
    if action2:
        print(f"✅ Найдено ПЕРВОЕ действие: {action2['action']}")
        print(f"   (Остальные проигнорированы - это правильно!)")
    else:
        print("❌ Действие не найдено")

    # Тест 3: Чистый текст без действий
    print("\n3. Чистый текст (диалог, без действий):")
    response3 = "В каком городе ты хочешь заказать пиццу?"

    action3 = agent.parse_action(response3)
    if action3:
        print(f"❌ Ложное срабатывание: {action3}")
    else:
        print("✅ Действие не найдено (правильно, это диалог)")

    # Тест 4: JSON без поля action
    print("\n4. JSON без поля action:")
    response4 = """Вот информация:
{"name": "Маргарита", "price": 395}"""

    action4 = agent.parse_action(response4)
    if action4:
        print(f"❌ Ложное срабатывание: {action4}")
    else:
        print("✅ Действие не найдено (правильно, это не команда)")

    # Тест 5: Невалидный JSON (без кавычек)
    print("\n5. Невалидный JSON (автоисправление):")
    response5 = """Открываю страницу.
{action: navigate, params: {url: "https://example.com"}, reasoning: "test"}"""

    action5 = agent.parse_action(response5)
    if action5:
        print(f"✅ Найдено действие после автоисправления: {action5['action']}")
    else:
        print("❌ Не удалось распарсить (нужно улучшить автоисправление)")

    print("\n" + "=" * 70)
    print("ТЕСТ ЗАВЕРШЁН")
    print("=" * 70)

if __name__ == "__main__":
    test_parse_action()
