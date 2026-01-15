#!/usr/bin/env python3
"""
Тест обработки команд выхода и благодарности
Проверяет, что агент корректно распознаёт различные варианты прощания
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_current_exit_logic():
    """Тест ТЕКУЩЕЙ логики выхода"""
    print("=" * 70)
    print("🧪 ТЕСТ: Текущая логика обработки выхода")
    print("=" * 70)

    # Текущий код из dialogue_manager.py:66
    exit_keywords = ['exit', 'quit', 'выход', 'пока']

    test_cases = [
        # Формат: (ввод пользователя, ожидаемый результат, описание)
        ("пока", True, "Простое 'пока'"),
        ("Пока", True, "С заглавной буквы"),
        ("ПОКА", True, "Все заглавные"),
        ("exit", True, "Английский exit"),
        ("quit", True, "Английский quit"),
        ("выход", True, "Русский выход"),

        # ПРОБЛЕМНЫЕ СЛУЧАИ
        ("Спасибо. Пока", False, "Благодарность + пока"),
        ("Пока, спасибо", False, "Пока + благодарность"),
        ("Всё, пока", False, "Префикс + пока"),
        ("До свидания", False, "Альтернативное прощание"),
        ("Спасибо за помощь, пока", False, "Длинная фраза с пока"),
        ("пока!", False, "С восклицательным знаком"),
        ("До встречи", False, "Другое прощание"),
        ("Спасибо", False, "Только благодарность"),
        ("прощай", False, "Ещё вариант прощания"),
        ("Ладно, пока", False, "Фраза с пока"),
    ]

    print("\n📊 Проверка текущей логики:")
    print(f"   Код: if user_input.lower() in {exit_keywords}\n")

    passed = 0
    failed = 0
    problems = []

    for user_input, expected_exit, description in test_cases:
        # Текущая логика
        should_exit = user_input.lower() in exit_keywords

        status = "✅" if should_exit == expected_exit else "❌"

        if should_exit == expected_exit:
            passed += 1
        else:
            failed += 1
            problems.append((user_input, should_exit, expected_exit, description))

        print(f"{status} '{user_input}' → {'EXIT' if should_exit else 'CONTINUE'} ({description})")

    print("\n" + "=" * 70)
    print(f"Результат: {passed} ✅ | {failed} ❌")

    if problems:
        print("\n⚠️  ПРОБЛЕМНЫЕ СЛУЧАИ (НЕ РАБОТАЮТ):")
        for inp, actual, expected, desc in problems:
            print(f"   '{inp}': получено {actual}, ожидалось {expected}")
            print(f"      → {desc}")

    print("=" * 70)

    return len(problems) == 0


def test_proposed_exit_logic():
    """Тест ПРЕДЛАГАЕМОЙ логики выхода"""
    print("\n\n" + "=" * 70)
    print("🧪 ТЕСТ: Предлагаемая улучшенная логика")
    print("=" * 70)

    def should_exit(user_input: str) -> bool:
        """Улучшенная проверка на выход"""
        text = user_input.lower().strip()

        # Список слов-прощаний
        exit_words = [
            'пока', 'выход', 'exit', 'quit',
            'до свидания', 'до встречи', 'прощай',
            'досвидания', 'довстречи'
        ]

        # Проверяем наличие хотя бы одного слова прощания
        for word in exit_words:
            if word in text:
                return True

        return False

    test_cases = [
        # Формат: (ввод пользователя, ожидаемый результат, описание)
        ("пока", True, "Простое 'пока'"),
        ("Пока", True, "С заглавной буквы"),
        ("ПОКА", True, "Все заглавные"),
        ("exit", True, "Английский exit"),
        ("quit", True, "Английский quit"),
        ("выход", True, "Русский выход"),

        # УЛУЧШЕННЫЕ СЛУЧАИ
        ("Спасибо. Пока", True, "Благодарность + пока"),
        ("Пока, спасибо", True, "Пока + благодарность"),
        ("Всё, пока", True, "Префикс + пока"),
        ("До свидания", True, "Альтернативное прощание"),
        ("Спасибо за помощь, пока", True, "Длинная фраза с пока"),
        ("пока!", True, "С восклицательным знаком"),
        ("До встречи", True, "Другое прощание"),
        ("прощай", True, "Ещё вариант прощания"),
        ("Ладно, пока", True, "Фраза с пока"),

        # НЕ ДОЛЖНЫ СРАБАТЫВАТЬ
        ("Спасибо", False, "Только благодарность"),
        ("Хорошо", False, "Согласие"),
        ("Давай", False, "Призыв к действию"),
        ("Покажи меню", False, "Слово 'пока' как часть другого слова"),
    ]

    print("\n📊 Проверка предлагаемой логики:")
    print("   Метод: проверка наличия слов-прощаний в тексте\n")

    passed = 0
    failed = 0
    problems = []

    for user_input, expected_exit, description in test_cases:
        result = should_exit(user_input)

        status = "✅" if result == expected_exit else "❌"

        if result == expected_exit:
            passed += 1
        else:
            failed += 1
            problems.append((user_input, result, expected_exit, description))

        print(f"{status} '{user_input}' → {'EXIT' if result else 'CONTINUE'} ({description})")

    print("\n" + "=" * 70)
    print(f"Результат: {passed} ✅ | {failed} ❌")

    if problems:
        print("\n⚠️  ПРОБЛЕМНЫЕ СЛУЧАИ:")
        for inp, actual, expected, desc in problems:
            print(f"   '{inp}': получено {actual}, ожидалось {expected}")
            print(f"      → {desc}")
    else:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОШЛИ!")

    print("=" * 70)

    return len(problems) == 0


def test_edge_cases():
    """Тест граничных случаев"""
    print("\n\n" + "=" * 70)
    print("🧪 ТЕСТ: Граничные случаи")
    print("=" * 70)

    def should_exit(user_input: str) -> bool:
        """Улучшенная проверка на выход"""
        text = user_input.lower().strip()

        exit_words = [
            'пока', 'выход', 'exit', 'quit',
            'до свидания', 'до встречи', 'прощай',
            'досвидания', 'довстречи'
        ]

        for word in exit_words:
            if word in text:
                return True

        return False

    edge_cases = [
        # Формат: (ввод, должен_выйти, описание)
        ("", False, "Пустая строка"),
        ("   ", False, "Только пробелы"),
        ("п", False, "Одна буква"),
        ("Покажи пиццу", False, "Слово 'пока' внутри другого слова - ЛОЖНОЕ СРАБАТЫВАНИЕ!"),
        ("Пока не голоден", False, "'Пока' в другом контексте - ЛОЖНОЕ СРАБАТЫВАНИЕ!"),
        ("   пока   ", True, "Пробелы вокруг"),
        ("ПОКА!!!", True, "С символами"),
        ("Ну пока тогда", True, "Фраза с пока"),
    ]

    print("\n📊 Проверка граничных случаев:\n")

    problems = []

    for user_input, expected, description in edge_cases:
        result = should_exit(user_input)

        status = "✅" if result == expected else "⚠️"

        if result != expected:
            problems.append((user_input, result, expected, description))

        print(f"{status} '{user_input}' → {'EXIT' if result else 'CONTINUE'}")
        print(f"   {description}")
        if result != expected:
            print(f"   ⚠️  ПРОБЛЕМА: получено {result}, ожидалось {expected}")
        print()

    print("=" * 70)

    if problems:
        print(f"\n⚠️  Обнаружено {len(problems)} проблем с граничными случаями")
        print("\nВАЖНО: Ложные срабатывания при наличии 'пока' в других словах!")
        print("Решение: использовать разделение на слова (word boundaries)")

    return problems


def main():
    """Запуск всех тестов"""
    print("\n" + "=" * 70)
    print("🧪 ТЕСТИРОВАНИЕ ОБРАБОТКИ КОМАНД ВЫХОДА")
    print("=" * 70)

    results = []

    # Тест 1: Текущая логика
    result1 = test_current_exit_logic()
    results.append(("Текущая логика", result1))

    # Тест 2: Предлагаемая логика
    result2 = test_proposed_exit_logic()
    results.append(("Предлагаемая логика", result2))

    # Тест 3: Граничные случаи
    edge_problems = test_edge_cases()
    results.append(("Граничные случаи", len(edge_problems) == 0))

    # Итоги
    print("\n\n" + "=" * 70)
    print("📊 ФИНАЛЬНЫЕ ИТОГИ")
    print("=" * 70)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"\n{status} - {name}")

    print("\n" + "=" * 70)

    # Рекомендации
    print("\n💡 РЕКОМЕНДАЦИИ:\n")
    print("1. Текущая логика НЕ работает для комбинаций типа 'Спасибо. Пока'")
    print("2. Простая проверка 'in text' вызывает ложные срабатывания:")
    print("   - 'Покажи' содержит 'пока'")
    print("   - 'Пока не голоден' тоже содержит 'пока'")
    print("\n3. ЛУЧШЕЕ РЕШЕНИЕ: использовать регулярные выражения с word boundaries")
    print("   Пример: r'\\b(пока|выход|exit|quit|до свидания)\\b'")
    print("\n4. Это позволит:")
    print("   ✅ Распознавать 'Спасибо. Пока'")
    print("   ✅ Игнорировать 'Покажи меню'")
    print("   ✅ Игнорировать 'Пока не голоден'")
    print("=" * 70)

    return 0 if all(r for _, r in results) else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
