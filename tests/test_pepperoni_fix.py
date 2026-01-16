#!/usr/bin/env python3
"""
Тестовый сценарий для проверки исправления проблемы с презентацией блюд

Проверяет:
1. Агент показывает варианты БЕЗ открытия карточек
2. После выбора пользователя агент использует правильную последовательность:
   - scroll_down
   - wait_for_text
   - click_by_text
   - wait_for_modal
   - get_modal_text
3. Агент не начинает поиск заново
"""
import asyncio
import sys
from src.agent.specialized_agents import ShoppingAgent, AgentSelector

def test_shopping_agent_prompt():
    """Проверить что промпт содержит правильные инструкции"""
    agent = ShoppingAgent()
    prompt = agent.get_system_prompt()

    print("=" * 70)
    print("ПРОВЕРКА ПРОМПТА ShoppingAgent")
    print("=" * 70)

    # Проверка 1: Есть инструкция про wait_for_text
    checks = {
        "wait_for_text инструкция": "wait_for_text" in prompt,
        "wait_for_modal инструкция": "wait_for_modal" in prompt,
        "scroll_down перед кликом": "scroll_down" in prompt and "ПЕРЕД кликом" in prompt or "Докручиваю" in prompt,
        "Два сценария презентации": "СЦЕНАРИЙ 1" in prompt and "СЦЕНАРИЙ 2" in prompt,
        "НЕ ОТКРЫВАЙ карточки": "НЕ ОТКРЫВАЙ карточки" in prompt or "НЕ открывал" in prompt,
        "5 шагов обязательны": "5 ШАГОВ ОБЯЗАТЕЛЬНЫ" in prompt or "ВСЕ 5 ШАГОВ" in prompt,
    }

    all_passed = True
    for check_name, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"{status} {check_name}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 70)
    if all_passed:
        print("✅ ВСЕ ПРОВЕРКИ ПРОШЛИ!")
        print("\nПромпт агента содержит правильные инструкции:")
        print("- Показывать варианты БЕЗ открытия карточек")
        print("- Использовать wait_for_text перед кликом")
        print("- Использовать wait_for_modal после клика")
        print("- Следовать последовательности из 5 шагов")
    else:
        print("❌ НЕКОТОРЫЕ ПРОВЕРКИ НЕ ПРОШЛИ")
        print("Промпт агента требует доработки")

    print("=" * 70)
    return all_passed

def test_agent_selection():
    """Проверить что агент корректно выбирается для заказа еды"""
    print("\n" + "=" * 70)
    print("ПРОВЕРКА ВЫБОРА АГЕНТА")
    print("=" * 70)

    test_messages = [
        ("Пепперони хочу", "shopping"),
        ("Хочу пиццу", "shopping"),
        ("Найди бургер", "shopping"),
        ("Закажи роллы", "shopping"),
    ]

    all_passed = True
    for message, expected_type in test_messages:
        task_type, agent = AgentSelector.select_agent(message)
        actual_type = task_type.value

        passed = actual_type == expected_type
        status = "✅" if passed else "❌"

        print(f"{status} '{message}' -> {actual_type} (ожидается: {expected_type})")

        if not passed:
            all_passed = False

    print("=" * 70)
    if all_passed:
        print("✅ ВСЕ ПРОВЕРКИ ВЫБОРА АГЕНТА ПРОШЛИ!")
    else:
        print("❌ НЕКОТОРЫЕ ПРОВЕРКИ НЕ ПРОШЛИ")
    print("=" * 70)

    return all_passed

def print_key_improvements():
    """Показать ключевые улучшения в промпте"""
    print("\n" + "=" * 70)
    print("КЛЮЧЕВЫЕ УЛУЧШЕНИЯ В ПРОМПТЕ")
    print("=" * 70)

    improvements = [
        "1. Добавлена секция 'КРИТИЧЕСКИ ВАЖНО: ОЖИДАНИЕ ЗАГРУЗКИ ЭЛЕМЕНТОВ'",
        "   - Обязательная последовательность из 5 шагов",
        "   - scroll_down → wait_for_text → click_by_text → wait_for_modal → get_modal_text",
        "",
        "2. Разделены ДВА СЦЕНАРИЯ презентации:",
        "   - Сценарий 1: Показать варианты БЕЗ открытия карточек (для выбора)",
        "   - Сценарий 2: Презентовать одно блюдо С составом (после выбора)",
        "",
        "3. Добавлены примеры ПРАВИЛЬНОЙ и НЕПРАВИЛЬНОЙ последовательности",
        "   - Показано что НЕ нужно кликать сразу",
        "   - Показано как обрабатывать ошибки (повторить с ожиданием)",
        "",
        "4. Усилены инструкции про контекст:",
        "   - НЕ ОТКРЫВАЙ карточки на этапе показа вариантов",
        "   - НЕ начинай поиск заново если пользователь выбрал вариант",
        "   - ИСПОЛЬЗУЙ уже найденные результаты",
    ]

    for line in improvements:
        print(line)

    print("=" * 70)

def main():
    """Главная функция теста"""
    print("\n🧪 ТЕСТИРОВАНИЕ ИСПРАВЛЕНИЙ ДЛЯ ShoppingAgent\n")

    # Тест 1: Проверка промпта
    prompt_test_passed = test_shopping_agent_prompt()

    # Тест 2: Проверка выбора агента
    selection_test_passed = test_agent_selection()

    # Показать улучшения
    print_key_improvements()

    # Итоговый результат
    print("\n" + "=" * 70)
    print("ИТОГОВЫЙ РЕЗУЛЬТАТ")
    print("=" * 70)

    if prompt_test_passed and selection_test_passed:
        print("✅ ВСЕ ТЕСТЫ ПРОШЛИ УСПЕШНО!")
        print("\n📝 Рекомендация: Запустите реальный тест с командой:")
        print("   python main.py")
        print("\n   И попробуйте сценарий:")
        print("   1. 'Пепперони хочу'")
        print("   2. Агент должен показать варианты")
        print("   3. 'Третий вариант' или 'Пепперони премиум'")
        print("   4. Агент должен использовать последовательность:")
        print("      scroll_down → wait_for_text → click → wait_for_modal → get_modal_text")
        print("\n   Агент НЕ должен:")
        print("   - Кликать сразу без wait_for_text")
        print("   - Пытаться читать модалку без wait_for_modal")
        print("   - Начинать поиск заново на другом сайте")
        return 0
    else:
        print("❌ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОШЛИ")
        print("\nПроверьте промпт в файле:")
        print("   src/agent/specialized_agents.py")
        return 1

if __name__ == "__main__":
    sys.exit(main())
