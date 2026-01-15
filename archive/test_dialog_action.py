#!/usr/bin/env python3
"""
Тест проблемы с действием "dialog"
Проверяет, почему агент генерирует {"action": "dialog"} несмотря на запрет в промпте
"""
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.agent.ai_agent import AIAgent


def test_parse_action_with_dialog():
    """Тест парсинга действия 'dialog'"""
    print("=" * 70)
    print("🧪 ТЕСТ: Парсинг действия 'dialog'")
    print("=" * 70)

    agent = AIAgent()

    test_cases = [
        # (ответ агента, ожидаемый результат, описание)
        (
            '{"action": "navigate", "params": {"url": "..."}}',
            {"action": "navigate", "params": {"url": "..."}},
            "Обычное действие navigate"
        ),
        (
            '{"action": "dialog", "text": "Привет!"}',
            {"action": "dialog", "text": "Привет!"},
            "Действие dialog (ПРОБЛЕМА)"
        ),
        (
            '{"action": "dialog", "params": {"message": "..."}}',
            {"action": "dialog", "params": {"message": "..."}},
            "Dialog с params"
        ),
        (
            'Просто текст без JSON',
            None,
            "Обычный текст (не действие)"
        ),
        (
            'Текст с JSON внутри: {"action": "dialog", "text": "..."}',
            {"action": "dialog", "text": "..."},
            "Dialog в тексте"
        ),
    ]

    print("\n📊 Проверка парсинга:\n")

    for response, expected, description in test_cases:
        parsed = agent.parse_action(response)

        if parsed == expected:
            status = "✅"
        else:
            status = "❌"

        print(f"{status} {description}")
        print(f"   Ответ: {response[:60]}...")
        print(f"   Parsed: {parsed}")
        print(f"   Expected: {expected}")
        print()

    print("=" * 70)


def test_prompt_instruction():
    """Проверка инструкции в промпте"""
    print("\n\n" + "=" * 70)
    print("🧪 ТЕСТ: Инструкция о 'dialog' в промпте")
    print("=" * 70)

    agent = AIAgent()
    agent.add_system_prompt()

    # Ищем инструкцию в системном промпте
    system_message = agent.conversation_history[0]
    prompt_text = system_message["content"]

    print("\n📝 Поиск упоминаний 'dialog' в промпте:\n")

    # Ищем строки с "dialog"
    lines = prompt_text.split('\n')
    dialog_mentions = []

    for i, line in enumerate(lines, 1):
        if 'dialog' in line.lower():
            dialog_mentions.append((i, line))

    if dialog_mentions:
        print(f"Найдено {len(dialog_mentions)} упоминаний 'dialog':\n")
        for line_num, line in dialog_mentions:
            print(f"   Строка {line_num}: {line.strip()}")
    else:
        print("❌ 'dialog' НЕ упоминается в промпте!")

    print("\n" + "=" * 70)

    # Проверка списка доступных действий
    print("\n📋 Список доступных действий в промпте:\n")

    in_actions_section = False
    actions = []

    for line in lines:
        if 'ДОСТУПНЫЕ ДЕЙСТВИЯ:' in line:
            in_actions_section = True
            continue

        if in_actions_section:
            if line.startswith('-'):
                actions.append(line.strip())
            elif line.strip() and not line.startswith(' '):
                break

    for action in actions:
        print(f"   {action}")

    print("\n" + "=" * 70)

    return len(dialog_mentions) > 0


def analyze_real_log():
    """Анализ реального лога где появился 'dialog'"""
    print("\n\n" + "=" * 70)
    print("🔍 АНАЛИЗ: Реальный случай из логов")
    print("=" * 70)

    # Из logs/dialogue_manager.log строка 69
    real_case = {
        "timestamp": "2026-01-14 17:49:07,338",
        "action": "dialog",
        "error": "Неизвестное действие: dialog"
    }

    print(f"\n⏰ Время: {real_case['timestamp']}")
    print(f"❌ Ошибка: {real_case['error']}")
    print(f"🔧 Попытка выполнить: {real_case['action']}")

    print("\n📊 Контекст из agent_responses.log:")

    # Ищем в логе что было до этого
    try:
        with open("logs/agent_responses.log", "r", encoding="utf-8") as f:
            content = f.read()

        # Ищем секции с dialog
        sections = content.split("============================================================")

        dialog_sections = [s for s in sections if "dialog" in s.lower()]

        if dialog_sections:
            print(f"\n   Найдено {len(dialog_sections)} секций с 'dialog' в agent_responses.log\n")

            for i, section in enumerate(dialog_sections[:3], 1):  # Показываем первые 3
                print(f"   --- Секция {i} ---")
                lines = section.strip().split('\n')[:10]  # Первые 10 строк
                for line in lines:
                    print(f"   {line}")
                print()
        else:
            print("\n   ❌ Секций с 'dialog' не найдено")

    except FileNotFoundError:
        print("\n   ⚠️  Файл logs/agent_responses.log не найден")

    print("=" * 70)


def test_action_executor_support():
    """Проверка поддержки 'dialog' в ActionExecutor"""
    print("\n\n" + "=" * 70)
    print("🧪 ТЕСТ: Поддержка 'dialog' в ActionExecutor")
    print("=" * 70)

    from src.agent.action_executor import ActionExecutor
    from src.tools.browser_tools import BrowserTools

    browser_tools = BrowserTools()
    executor = ActionExecutor(browser_tools)

    available_actions = executor.get_available_actions()

    print("\n📋 Доступные действия в ActionExecutor:\n")
    for action in available_actions:
        print(f"   ✓ {action}")

    print("\n" + "=" * 70)

    if "dialog" in available_actions:
        print("\n✅ 'dialog' ПОДДЕРЖИВАЕТСЯ в ActionExecutor")
        return True
    else:
        print("\n❌ 'dialog' НЕ ПОДДЕРЖИВАЕТСЯ в ActionExecutor")
        print("\n⚠️  ПРОБЛЕМА: Агент генерирует 'dialog', но ActionExecutor его не понимает!")
        return False


def propose_solution():
    """Предложение решения"""
    print("\n\n" + "=" * 70)
    print("💡 ПРЕДЛАГАЕМЫЕ РЕШЕНИЯ")
    print("=" * 70)

    print("\n🎯 ПРОБЛЕМА:")
    print("   Агент иногда генерирует {'action': 'dialog', ...} несмотря на запрет")
    print("   в промпте: 'НЕ используй {\"action\": \"dialog\"} - такого действия НЕТ!'")

    print("\n📋 ВОЗМОЖНЫЕ ПРИЧИНЫ:")
    print("   1. LLM игнорирует негативные инструкции ('НЕ делай X')")
    print("   2. Агент путается когда нужен диалог vs действие")
    print("   3. Недостаточно ясен формат для диалога")

    print("\n✅ РЕШЕНИЕ 1: Добавить поддержку 'dialog' в ActionExecutor")
    print("   Плюсы:")
    print("      + Агент сможет явно указывать когда нужен диалог")
    print("      + Унифицированный подход (всё через действия)")
    print("   Минусы:")
    print("      - Избыточно (уже работает через текст)")
    print("      - Усложняет код")

    print("\n✅ РЕШЕНИЕ 2: Улучшить промпт (позитивные инструкции)")
    print("   Вместо: 'НЕ используй dialog'")
    print("   Писать: 'Для диалога просто отвечай текстом БЕЗ JSON'")
    print("   Плюсы:")
    print("      + Более понятно для LLM")
    print("      + Позитивная формулировка")
    print("   Минусы:")
    print("      - Не гарантирует 100% решение")

    print("\n✅ РЕШЕНИЕ 3: Обработка 'dialog' как обычного текста")
    print("   В dialogue_manager.py при получении action='dialog':")
    print("   - Извлечь текст из action['text'] или action['params']['message']")
    print("   - Вывести как обычный ответ")
    print("   - Не бросать ошибку")
    print("   Плюсы:")
    print("      + Graceful fallback")
    print("      + Работает даже если агент ошибся")
    print("   Минусы:")
    print("      - Маскирует проблему вместо решения")

    print("\n🎯 РЕКОМЕНДУЕМОЕ РЕШЕНИЕ:")
    print("   Комбинация 2 + 3:")
    print("   1. Улучшить промпт (позитивные инструкции)")
    print("   2. Добавить graceful fallback для 'dialog'")
    print("   3. Логировать когда агент использует 'dialog' для мониторинга")

    print("\n" + "=" * 70)


def main():
    """Запуск всех тестов"""
    print("\n" + "=" * 70)
    print("🧪 ТЕСТИРОВАНИЕ ПРОБЛЕМЫ С ДЕЙСТВИЕМ 'dialog'")
    print("=" * 70)

    # Тест 1: Парсинг
    test_parse_action_with_dialog()

    # Тест 2: Инструкция в промпте
    has_dialog_instruction = test_prompt_instruction()

    # Тест 3: Анализ реального лога
    analyze_real_log()

    # Тест 4: Поддержка в ActionExecutor
    dialog_supported = test_action_executor_support()

    # Предложение решения
    propose_solution()

    # Итоги
    print("\n\n" + "=" * 70)
    print("📊 ФИНАЛЬНЫЕ ИТОГИ")
    print("=" * 70)

    print(f"\n✅ Промпт содержит запрет на 'dialog': {has_dialog_instruction}")
    print(f"❌ ActionExecutor поддерживает 'dialog': {dialog_supported}")

    print("\n⚠️  ВЫВОД:")
    print("   Агент генерирует 'dialog' несмотря на запрет в промпте,")
    print("   но ActionExecutor не умеет обрабатывать это действие.")
    print("   Результат: ошибка 'Неизвестное действие: dialog'")

    print("\n🎯 НЕОБХОДИМО:")
    print("   1. Улучшить промпт (позитивные инструкции)")
    print("   2. Добавить graceful fallback для 'dialog' в dialogue_manager.py")

    print("=" * 70)

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
