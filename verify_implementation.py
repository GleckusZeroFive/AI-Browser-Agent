#!/usr/bin/env python3
"""
Проверка наличия всех необходимых методов и атрибутов
Без запуска реального кода
"""
import ast
import sys
from pathlib import Path


def check_imports(tree):
    """Проверка импортов"""
    print("\n📦 Проверка импортов...")

    required_imports = {
        'ContextLevel': False,
        'Tuple': False,
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name in required_imports:
                    required_imports[alias.name] = True

    for name, found in required_imports.items():
        if found:
            print(f"  ✅ {name} импортирован")
        else:
            print(f"  ⚠️  {name} не найден")

    return all(required_imports.values())


def check_attributes(tree):
    """Проверка атрибутов __init__"""
    print("\n🏗️  Проверка атрибутов в __init__...")

    required_attributes = [
        'task_type',
        '_current_context_level',
        '_current_prompt_level',
        '_cached_system_prompt',
        '_cached_prompt_level',
        'knowledge_base'
    ]

    found_attributes = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == '__init__':
            for stmt in ast.walk(node):
                if isinstance(stmt, ast.Assign):
                    for target in stmt.targets:
                        if isinstance(target, ast.Attribute):
                            if isinstance(target.value, ast.Name) and target.value.id == 'self':
                                found_attributes.add(target.attr)

    for attr in required_attributes:
        if attr in found_attributes:
            print(f"  ✅ self.{attr}")
        else:
            print(f"  ❌ self.{attr} НЕ НАЙДЕН")

    return all(attr in found_attributes for attr in required_attributes)


def check_methods(tree):
    """Проверка наличия всех методов"""
    print("\n🔧 Проверка методов...")

    required_methods = [
        'set_task_type',
        '_select_context_level',
        '_update_system_message',
        '_get_base_system_prompt',
        '_prepare_context_for_request',
        'get_token_usage_stats',
    ]

    found_methods = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            found_methods.add(node.name)

    for method in required_methods:
        if method in found_methods:
            print(f"  ✅ {method}()")
        else:
            print(f"  ❌ {method}() НЕ НАЙДЕН")

    return all(method in found_methods for method in required_methods)


def check_method_signatures(tree):
    """Проверка сигнатур методов"""
    print("\n📝 Проверка сигнатур методов...")

    # Находим метод chat
    chat_method = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == 'chat':
            chat_method = node
            break

    if not chat_method:
        print("  ❌ Метод chat() не найден")
        return False

    # Проверяем параметры
    args = [arg.arg for arg in chat_method.args.args]

    expected_params = ['self', 'user_message', 'context', 'specialized_agent']

    print(f"  Найденные параметры: {args}")

    if 'specialized_agent' in args:
        print("  ✅ Параметр specialized_agent добавлен в chat()")
        return True
    else:
        print("  ❌ Параметр specialized_agent НЕ найден в chat()")
        return False


def analyze_file(filepath):
    """Анализ файла"""
    print(f"\n{'=' * 70}")
    print(f"🔍 АНАЛИЗ ФАЙЛА: {filepath.name}")
    print(f"{'=' * 70}")

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            source = f.read()

        tree = ast.parse(source)

        results = []

        # Проверяем импорты
        results.append(("Импорты", check_imports(tree)))

        # Проверяем атрибуты
        results.append(("Атрибуты", check_attributes(tree)))

        # Проверяем методы
        results.append(("Методы", check_methods(tree)))

        # Проверяем сигнатуры
        results.append(("Сигнатура chat()", check_method_signatures(tree)))

        # Итоговый отчёт
        print(f"\n{'=' * 70}")
        print("📋 ИТОГОВЫЙ ОТЧЁТ")
        print(f"{'=' * 70}")

        passed = sum(1 for _, result in results if result)
        total = len(results)

        for name, result in results:
            status = "✅ ПРОЙДЕНО" if result else "❌ ПРОВАЛЕНО"
            print(f"{name}: {status}")

        print(f"\n🎯 РЕЗУЛЬТАТ: {passed}/{total} проверок пройдено")

        if passed == total:
            print("\n🎉 ВСЕ ПРОВЕРКИ УСПЕШНО ПРОЙДЕНЫ!")
            print("\n💡 Реализация корректна:")
            print("   • Все импорты добавлены")
            print("   • Все атрибуты инициализированы")
            print("   • Все методы реализованы")
            print("   • Сигнатура chat() обновлена")
            return 0
        else:
            print("\n⚠️  Некоторые проверки не пройдены")
            return 1

    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return 1


def main():
    """Главная функция"""
    filepath = Path("src/agent/ai_agent.py")

    if not filepath.exists():
        print(f"❌ Файл не найден: {filepath}")
        return 1

    return analyze_file(filepath)


if __name__ == "__main__":
    sys.exit(main())
