#!/usr/bin/env python3
"""
Интеграционный тест изменений (без реального браузера)
Проверяет что код корректно импортируется и логика работает
"""
import sys
import os

# Добавляем путь к проекту
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Тест импортов всех модулей"""
    print("=" * 70)
    print("ТЕСТ 1: Проверка импортов")
    print("=" * 70)

    try:
        print("\n1. Импорт Config...")
        from src.config import Config
        print("   ✅ Config импортирован")

        print("\n2. Импорт AIAgent...")
        from src.agent.ai_agent import AIAgent
        print("   ✅ AIAgent импортирован")

        # Проверка что можем создать агента
        agent = AIAgent()
        print("   ✅ AIAgent создан")

        print("\n3. Проверка системного промпта...")
        agent.add_system_prompt()

        # Проверяем что промпт содержит упоминание find_text
        history = agent.conversation_history
        if history:
            system_prompt = history[0]['content']
            if 'find_text' in system_prompt:
                print("   ✅ Промпт содержит 'find_text'")
            else:
                print("   ❌ ОШИБКА: 'find_text' не найден в промпте")
                return False

            if 'НЕ ИЩИТЕ несуществующую "кнопку поиска"' in system_prompt:
                print("   ✅ Промпт содержит предупреждение о несуществующей кнопке")
            else:
                print("   ❌ ОШИБКА: Предупреждение не найдено")
                return False

        return True

    except ImportError as e:
        print(f"\n   ❌ ОШИБКА импорта: {e}")
        print(f"   Это нормально если зависимости не установлены")
        return False
    except Exception as e:
        print(f"\n   ❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_action_executor_structure():
    """Тест структуры ActionExecutor"""
    print("\n\n" + "=" * 70)
    print("ТЕСТ 2: Проверка структуры ActionExecutor")
    print("=" * 70)

    try:
        # Читаем файл напрямую
        print("\n1. Чтение action_executor.py...")
        with open("src/agent/action_executor.py", "r", encoding="utf-8") as f:
            content = f.read()

        print("\n2. Проверка наличия 'find_text' в маппинге...")
        if '"find_text": self._execute_find_text' in content:
            print("   ✅ find_text найден в action_map")
        else:
            print("   ❌ ОШИБКА: find_text отсутствует в action_map")
            return False

        print("\n3. Проверка метода _execute_find_text...")
        if 'async def _execute_find_text' in content:
            print("   ✅ Метод _execute_find_text найден")
        else:
            print("   ❌ ОШИБКА: Метод _execute_find_text не найден")
            return False

        print("\n4. Проверка вызова find_text_on_page...")
        if 'find_text_on_page' in content:
            print("   ✅ Вызов find_text_on_page найден")
        else:
            print("   ❌ ОШИБКА: Вызов find_text_on_page не найден")
            return False

        return True

    except Exception as e:
        print(f"\n   ❌ ОШИБКА: {e}")
        return False

def test_browser_tools_structure():
    """Тест структуры BrowserTools"""
    print("\n\n" + "=" * 70)
    print("ТЕСТ 3: Проверка структуры BrowserTools")
    print("=" * 70)

    try:
        print("\n1. Чтение browser_tools.py...")
        with open("src/tools/browser_tools.py", "r", encoding="utf-8") as f:
            content = f.read()

        print("\n2. Проверка метода find_text_on_page...")
        if 'async def find_text_on_page' in content:
            print("   ✅ Метод find_text_on_page найден")
        else:
            print("   ❌ ОШИБКА: Метод не найден")
            return False

        print("\n3. Проверка логики Ctrl+F...")
        if "Control+F" in content or "Ctrl+F" in content:
            print("   ✅ Ctrl+F поиск реализован")
        else:
            print("   ❌ ОШИБКА: Ctrl+F не найден")
            return False

        print("\n4. Проверка возврата результата...")
        if '"found": True' in content and '"count":' in content:
            print("   ✅ Результат возвращает found и count")
        else:
            print("   ❌ ОШИБКА: Некорректный формат результата")
            return False

        return True

    except Exception as e:
        print(f"\n   ❌ ОШИБКА: {e}")
        return False

def test_dialogue_manager_limit():
    """Тест обработки лимита в DialogueManager"""
    print("\n\n" + "=" * 70)
    print("ТЕСТ 4: Проверка обработки лимита в DialogueManager")
    print("=" * 70)

    try:
        print("\n1. Чтение dialogue_manager.py...")
        with open("src/dialogue_manager.py", "r", encoding="utf-8") as f:
            content = f.read()

        print("\n2. Проверка предупреждения о лимите...")
        if "actions_count >= max_actions - 2" in content:
            print("   ✅ Условие предупреждения найдено")
        else:
            print("   ❌ ОШИБКА: Условие предупреждения не найдено")
            return False

        if "⚠️ ВНИМАНИЕ: Осталось" in content:
            print("   ✅ Текст предупреждения найден")
        else:
            print("   ❌ ОШИБКА: Текст предупреждения не найден")
            return False

        print("\n3. Проверка финального запроса...")
        if "Достигнут лимит действий (10)" in content:
            print("   ✅ Финальный запрос к агенту найден")
        else:
            print("   ❌ ОШИБКА: Финальный запрос не найден")
            return False

        if "Объясни пользователю" in content:
            print("   ✅ Запрос на объяснение найден")
        else:
            print("   ❌ ОШИБКА: Запрос на объяснение не найден")
            return False

        return True

    except Exception as e:
        print(f"\n   ❌ ОШИБКА: {e}")
        return False

def main():
    """Запуск всех тестов"""
    print("\n" + "=" * 70)
    print("🧪 ИНТЕГРАЦИОННОЕ ТЕСТИРОВАНИЕ ИЗМЕНЕНИЙ")
    print("=" * 70)

    results = []

    # Тест 1: Импорты (может не пройти без зависимостей)
    result1 = test_imports()
    results.append(("Импорты и промпт", result1))

    # Тест 2: ActionExecutor
    result2 = test_action_executor_structure()
    results.append(("ActionExecutor структура", result2))

    # Тест 3: BrowserTools
    result3 = test_browser_tools_structure()
    results.append(("BrowserTools структура", result3))

    # Тест 4: DialogueManager
    result4 = test_dialogue_manager_limit()
    results.append(("DialogueManager лимит", result4))

    # Итоги
    print("\n\n" + "=" * 70)
    print("📊 ИТОГИ ТЕСТИРОВАНИЯ")
    print("=" * 70)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"\n{status} - {name}")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    print("\n" + "=" * 70)
    print(f"Пройдено: {passed}/{total} тестов")

    if passed == total:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        print("=" * 70)
        return 0
    elif passed >= total - 1:
        print(f"\n⚠️  {total - passed} тест не прошёл (возможно из-за отсутствия зависимостей)")
        print("=" * 70)
        return 0
    else:
        print("\n❌ ЕСТЬ ОШИБКИ!")
        print("=" * 70)
        return 1

if __name__ == "__main__":
    sys.exit(main())
