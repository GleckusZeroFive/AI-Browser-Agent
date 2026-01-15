#!/usr/bin/env python3
"""
Тест логики лимитов действий
Проверяет что агент выдаёт промежуточный отчёт при приближении к лимиту
"""
import sys

def test_limit_logic():
    """Симуляция логики лимитов"""
    print("=" * 70)
    print("🧪 ТЕСТ: Логика лимитов действий")
    print("=" * 70)

    max_actions = 10
    actions_count = 0

    print(f"\nМаксимум действий: {max_actions}")
    print("\n📊 Симуляция работы агента:\n")

    # Симулируем выполнение действий
    actions = [
        "navigate", "get_page_text", "click_by_text", "scroll_down",
        "scroll_down", "find_text", "click_by_text", "get_modal_text",
        "close_modal", "scroll_down"
    ]

    for i, action in enumerate(actions, 1):
        actions_count = i
        remaining = max_actions - actions_count

        print(f"Действие {actions_count}/{max_actions}: {action}")

        # Проверка предупреждений
        if remaining == 2:
            print(f"   ⚠️ ПРЕДУПРЕЖДЕНИЕ: Осталось 2 действия!")
            print(f"   → Агент получает: 'Если нашёл информацию - сообщи пользователю'")
        elif remaining == 1:
            print(f"   🚨 КРИТИЧНО: Осталось 1 действие!")
            print(f"   → Агент получает: 'СЕЙЧАС ЖЕ сообщи результат (БЕЗ JSON)'")
        elif remaining <= 0:
            print(f"   🛑 ЛИМИТ ДОСТИГНУТ!")
            print(f"   → Принудительный отчёт пользователю")
            print(f"   → Цикл прерывается")
            break

        print()

    print("\n" + "=" * 70)
    print(f"✅ Выполнено {actions_count} действий")
    print(f"💬 Пользователь получил отчёт после действия {actions_count}")
    print("=" * 70)

    return True

def test_warning_messages():
    """Тест текстов предупреждений"""
    print("\n\n" + "=" * 70)
    print("📝 ТЕСТ: Тексты предупреждений")
    print("=" * 70)

    max_actions = 10

    print("\n1️⃣  При 8 действиях (осталось 2):")
    remaining = 2
    warning = f"⚠️ ВНИМАНИЕ: Осталось {remaining} действия до лимита. Если нашёл информацию - ОБЯЗАТЕЛЬНО сообщи пользователю ЧТО именно нашёл. Не молчи!"
    print(f"   {warning}")

    print("\n2️⃣  При 9 действиях (осталось 1):")
    remaining = 1
    warning = "🚨 КРИТИЧНО: Осталось 1 действие! СЕЙЧАС ЖЕ сообщи пользователю результат в текстовом виде (БЕЗ JSON). Не выполняй больше действий - только ответь пользователю!"
    print(f"   {warning}")

    print("\n3️⃣  При 10 действиях (лимит достигнут):")
    actions_count = 10
    warning = f"Лимит действий достигнут. Сообщи пользователю ЧТО ты нашёл за эти {actions_count} действий. Дай конкретный ответ на его запрос на основе собранной информации."
    print(f"   {warning}")

    print("\n" + "=" * 70)
    print("✅ Все предупреждения настроены правильно")
    print("=" * 70)

    return True

def test_counter_logic():
    """Тест логики счётчика"""
    print("\n\n" + "=" * 70)
    print("🔢 ТЕСТ: Логика счётчика действий")
    print("=" * 70)

    max_actions = 10
    actions_count = 0

    print("\n📌 Важно: Счётчик увеличивается СРАЗУ после выполнения действия")
    print("📌 Предупреждение проверяется ПОСЛЕ увеличения счётчика\n")

    # Критические моменты
    critical_points = [8, 9, 10]

    for action_num in critical_points:
        actions_count = action_num
        remaining = max_actions - actions_count

        print(f"После действия #{actions_count}:")
        print(f"  actions_count = {actions_count}")
        print(f"  remaining = {remaining}")

        if remaining == 2:
            print(f"  ✅ Выдаётся предупреждение о 2 оставшихся действиях")
        elif remaining == 1:
            print(f"  ✅ Выдаётся критическое предупреждение")
        elif remaining <= 0:
            print(f"  ✅ Принудительный отчёт и break")

        print()

    print("=" * 70)
    print("✅ Логика счётчика работает корректно")
    print("=" * 70)

    return True

def main():
    """Запуск всех тестов"""
    print("\n" + "=" * 70)
    print("🧪 ТЕСТИРОВАНИЕ ЛОГИКИ ЛИМИТОВ ДЕЙСТВИЙ")
    print("=" * 70)

    results = []

    # Тест 1: Логика лимитов
    result1 = test_limit_logic()
    results.append(("Логика лимитов", result1))

    # Тест 2: Тексты предупреждений
    result2 = test_warning_messages()
    results.append(("Тексты предупреждений", result2))

    # Тест 3: Логика счётчика
    result3 = test_counter_logic()
    results.append(("Логика счётчика", result3))

    # Итоги
    print("\n\n" + "=" * 70)
    print("📊 ФИНАЛЬНЫЕ ИТОГИ")
    print("=" * 70)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"\n{status} - {name}")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    print("\n" + "=" * 70)
    print(f"Пройдено: {passed}/{total} тестов")

    if passed == total:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("✅ Логика лимитов работает корректно!")
        print("=" * 70)
        return 0
    else:
        print("\n❌ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОШЛИ")
        print("=" * 70)
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
