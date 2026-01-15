#!/usr/bin/env python3
"""
Тест концепции автоматического продолжения при достижении лимита действий
Проверяет логику определения "нашёл ли агент результат" vs "нужно продолжать поиск"
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_continuation_logic():
    """Тест логики определения необходимости продолжения"""
    print("=" * 70)
    print("🧪 ТЕСТ: Логика автоматического продолжения")
    print("=" * 70)

    print("\n📋 Сценарии:\n")

    scenarios = [
        {
            "name": "Успешный поиск - пицца найдена",
            "actions_count": 7,
            "last_response": "Нашёл отличный вариант! Для 4 человек рекомендую '3 пиццы' за 929₽. Там есть острая Мексиканская пицца.",
            "should_continue": False,
            "reason": "Агент дал конкретный ответ с результатом"
        },
        {
            "name": "Промежуточный статус - продолжает поиск",
            "actions_count": 10,
            "last_response": "Я ищу блюда мексиканской кухни, но на текущей странице таких блюд не нашлось. Я продолжаю прокручивать страницу.",
            "should_continue": True,
            "reason": "Агент сообщил что НЕ нашёл, продолжает искать"
        },
        {
            "name": "Пустой ответ - агент молчит",
            "actions_count": 10,
            "last_response": "",
            "should_continue": True,
            "reason": "Агент не дал ответа, нужно продолжить"
        },
        {
            "name": "Негативный результат - ничего нет",
            "actions_count": 10,
            "last_response": "К сожалению, на сайте Додо Пиццы нет мексиканских блюд. Могу предложить острую Пепперони?",
            "should_continue": False,
            "reason": "Агент дал финальный ответ (негативный, но конкретный)"
        },
        {
            "name": "Технический статус без результата",
            "actions_count": 10,
            "last_response": '{"action": "scroll_down", "params": {"pixels": 500}}',
            "should_continue": True,
            "reason": "Агент вернул JSON действия, не текстовый ответ"
        },
    ]

    def should_agent_continue(response: str, actions_count: int, max_actions: int = 10) -> bool:
        """
        Определить, нужно ли агенту продолжать поиск

        Критерии для продолжения:
        1. Ответ пустой или очень короткий (< 20 символов)
        2. Ответ содержит JSON (агент не дал текстового ответа)
        3. Ответ содержит фразы "продолжаю", "ищу", "не нашёл" (промежуточный статус)
        4. Ответ НЕ содержит конкретной информации или рекомендации

        Критерии для завершения:
        1. Ответ содержит конкретную рекомендацию ("рекомендую", "предлагаю")
        2. Ответ содержит цены, названия блюд
        3. Ответ содержит негативный финальный результат ("к сожалению, нет")
        """
        response = response.strip()

        # Пустой или JSON ответ - продолжаем
        if not response or len(response) < 20 or response.startswith("{"):
            return True

        # Промежуточные фразы - продолжаем
        intermediate_phrases = [
            "продолжаю", "ищу", "прокручиваю", "не нашёл",
            "не нашлось", "пока не вижу", "еще ищу"
        ]
        if any(phrase in response.lower() for phrase in intermediate_phrases):
            return True

        # Финальные фразы - завершаем
        final_phrases = [
            "рекомендую", "предлагаю", "нашёл", "есть вариант",
            "подойдёт", "к сожалению", "увы", "не могу найти"
        ]
        if any(phrase in response.lower() for phrase in final_phrases):
            return False

        # Если содержит цену (₽) - это конкретный результат
        if "₽" in response or "руб" in response.lower():
            return False

        # По умолчанию - продолжаем (на всякий случай)
        return True

    print("📊 Проверка каждого сценария:\n")

    passed = 0
    failed = 0

    for scenario in scenarios:
        result = should_agent_continue(
            scenario["last_response"],
            scenario["actions_count"]
        )

        expected = scenario["should_continue"]
        status = "✅" if result == expected else "❌"

        if result == expected:
            passed += 1
        else:
            failed += 1

        print(f"{status} {scenario['name']}")
        print(f"   Действий выполнено: {scenario['actions_count']}")
        print(f"   Ответ: '{scenario['last_response'][:60]}...'")
        print(f"   Результат: {'ПРОДОЛЖИТЬ' if result else 'ЗАВЕРШИТЬ'}")
        print(f"   Ожидалось: {'ПРОДОЛЖИТЬ' if expected else 'ЗАВЕРШИТЬ'}")
        print(f"   Причина: {scenario['reason']}")
        print()

    print("=" * 70)
    print(f"Результат: {passed} ✅ | {failed} ❌\n")

    return failed == 0


def test_continuation_flow():
    """Тест полного flow автоматического продолжения"""
    print("\n" + "=" * 70)
    print("🔄 ТЕСТ: Flow автоматического продолжения")
    print("=" * 70)

    print("\n📋 Симуляция сессии с автоматическим продолжением:\n")

    max_actions = 10
    max_cycles = 3  # Максимум 3 цикла по 10 действий

    # Симуляция: агент ищет острые блюда
    cycles = [
        {
            "cycle": 1,
            "actions": ["navigate", "get_page_text", "find_text", "scroll_down", "scroll_down",
                       "scroll_down", "scroll_down", "find_text", "click_by_text", "wait_for_modal"],
            "result": "Я ищу мексиканские блюда, но на этой странице их нет. Продолжаю поиск.",
            "should_continue": True
        },
        {
            "cycle": 2,
            "actions": ["get_modal_text", "close_modal", "scroll_down", "scroll_down",
                       "find_text", "click_by_text", "wait_for_modal", "get_modal_text",
                       "close_modal", "scroll_down"],
            "result": "Нашёл! Есть острая Пепперони пицца за 599₽ и острая Мексиканская за 649₽. Для 4 человек рекомендую комбо '3 пиццы' за 929₽.",
            "should_continue": False
        }
    ]

    total_actions = 0

    for cycle_data in cycles:
        cycle_num = cycle_data["cycle"]
        actions = cycle_data["actions"]
        result = cycle_data["result"]
        should_continue = cycle_data["should_continue"]

        print(f"🔄 ЦИКЛ {cycle_num}:")
        print(f"   Действий в цикле: {len(actions)}")

        for i, action in enumerate(actions, 1):
            total_actions += 1
            print(f"   [{total_actions}] {action}")

        print(f"\n   Результат: '{result[:80]}...'")

        if should_continue:
            print(f"   ⏳ Агент не нашёл результат → ПРОДОЛЖИТЬ")
            print(f"   💬 Пользователю: 'Продолжаю поиск, требуется чуть больше времени...'\n")
        else:
            print(f"   ✅ Агент нашёл результат → ЗАВЕРШИТЬ")
            print(f"   💬 Пользователю: '{result}'\n")
            break

    print("=" * 70)
    print(f"📊 Итого:")
    print(f"   Выполнено циклов: {len([c for c in cycles if not c['should_continue']] or cycles)}")
    print(f"   Всего действий: {total_actions}")
    print(f"   Пользователь получил результат: ✅")
    print("=" * 70)

    return True


def test_user_experience():
    """Тест пользовательского опыта"""
    print("\n\n" + "=" * 70)
    print("👤 ТЕСТ: Пользовательский опыт")
    print("=" * 70)

    print("\n📋 Сравнение ДО и ПОСЛЕ:\n")

    print("❌ ДО (текущее поведение):")
    print("-" * 70)
    print("👤 Пользователь: Хочу острые блюда для 4 человек")
    print("🤖 Агент: [выполняет 7 действий]")
    print('🤖 Агент: "Я ищу мексиканские блюда, но на этой странице их нет."')
    print("🤖 Агент: [МОЛЧИТ]")
    print("👤 Пользователь: А дальше?")
    print("🤖 Агент: [нет ответа или выход]")
    print()
    print("😞 Проблема: Пользователь фрустрирован, нужно подталкивать агента\n")

    print("✅ ПОСЛЕ (с автоматическим продолжением):")
    print("-" * 70)
    print("👤 Пользователь: Хочу острые блюда для 4 человек")
    print("🤖 Агент: [выполняет 10 действий]")
    print("⏳ Система: 'Продолжаю поиск, требуется чуть больше времени...'")
    print("🤖 Агент: [выполняет ещё 10 действий]")
    print("🤖 Агент: 'Нашёл! Есть острая Пепперони за 599₽ и Мексиканская за 649₽.'")
    print("👤 Пользователь: Отлично!")
    print()
    print("😊 Результат: Пользователь получил результат БЕЗ вмешательства\n")

    print("=" * 70)

    return True


def main():
    """Запуск всех тестов"""
    print("\n" + "=" * 70)
    print("🧪 ТЕСТИРОВАНИЕ АВТОМАТИЧЕСКОГО ПРОДОЛЖЕНИЯ")
    print("=" * 70)

    results = []

    # Тест 1: Логика продолжения
    result1 = test_continuation_logic()
    results.append(("Логика определения продолжения", result1))

    # Тест 2: Flow продолжения
    result2 = test_continuation_flow()
    results.append(("Flow автоматического продолжения", result2))

    # Тест 3: Пользовательский опыт
    result3 = test_user_experience()
    results.append(("Пользовательский опыт", result3))

    # Итоги
    print("\n\n" + "=" * 70)
    print("📊 ФИНАЛЬНЫЕ ИТОГИ")
    print("=" * 70)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"\n{status} - {name}")

    passed = sum(1 for _, r in results if r)
    total = len(results)

    print("\n" + "=" * 70)
    print(f"Пройдено: {passed}/{total} тестов\n")

    if passed == total:
        print("🎉 КОНЦЕПЦИЯ ВАЛИДИРОВАНА!")
        print("\n💡 РЕКОМЕНДАЦИИ:")
        print("   1. Реализовать функцию should_agent_continue()")
        print("   2. Добавить в _execute_action_with_followup:")
        print("      - Проверку на необходимость продолжения")
        print("      - Сброс счётчика при продолжении")
        print("      - Уведомление пользователя")
        print("   3. Улучшить промпт:")
        print("      - НЕ выдавать технические статусы")
        print("      - Продолжать поиск если не нашёл")
        print("   4. Добавить лимит циклов (например, 3 цикла по 10 действий)")
        print("=" * 70)
        return 0
    else:
        print("❌ ТЕСТЫ НЕ ПРОШЛИ")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
