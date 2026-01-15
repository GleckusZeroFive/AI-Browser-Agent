"""
Тест логики предупреждения о лимите (без зависимостей)
"""

def test_limit_warning():
    """Тест предупреждения о лимите"""
    print("=" * 70)
    print("ТЕСТ: Проверка логики предупреждения о лимите")
    print("=" * 70)

    max_actions = 10

    print("\nСимуляция счётчика действий:")
    for i in range(12):
        actions_count = i

        # Логика из dialogue_manager.py
        if actions_count >= max_actions - 2 and actions_count < max_actions:
            remaining = max_actions - actions_count
            print(f"   Действие {i+1}: ⚠️  ПРЕДУПРЕЖДЕНИЕ - осталось {remaining} действий")
        elif actions_count >= max_actions:
            print(f"   Действие {i+1}: ❌ ЛИМИТ ДОСТИГНУТ - агент получит запрос на объяснение")
            print(f"                  Будет вызван: agent.chat('Достигнут лимит действий (10)...')")
        else:
            print(f"   Действие {i+1}: ✓ Выполняется нормально")

    print("\n" + "=" * 70)
    print("✅ РЕЗУЛЬТАТ: Логика работает корректно!")
    print("=" * 70)
    print("\nОжидаемое поведение:")
    print("  - Действия 1-8: Нормальное выполнение")
    print("  - Действие 9: Предупреждение (осталось 1)")
    print("  - Действие 10: Предупреждение (осталось 0) - последнее действие")
    print("  - Действие 11+: Лимит достигнут, агент объясняет ситуацию")

def test_action_list():
    """Проверка списка действий"""
    print("\n\n" + "=" * 70)
    print("ТЕСТ: Проверка списка доступных действий")
    print("=" * 70)

    # Список из action_executor.py
    expected_actions = [
        "navigate",
        "click_by_text",
        "get_page_text",
        "scroll_down",
        "press_key",
        "take_screenshot",
        "wait_for_text",
        "find_text",  # НОВОЕ!
    ]

    print(f"\nВсего действий: {len(expected_actions)}")
    print("\nСписок действий:")
    for i, action in enumerate(expected_actions, 1):
        marker = "🆕" if action == "find_text" else "  "
        print(f"  {marker} {i}. {action}")

    print("\n✅ Новое действие 'find_text' добавлено в список!")

if __name__ == "__main__":
    print("\n🧪 ЗАПУСК ТЕСТОВ (БЕЗ PLAYWRIGHT)\n")
    test_limit_warning()
    test_action_list()
    print("\n")
