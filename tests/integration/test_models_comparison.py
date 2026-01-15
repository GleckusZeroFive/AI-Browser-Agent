#!/usr/bin/env python3
"""
Тестирование и сравнение моделей Groq для AI агента

Критерии оценки:
1. Качество следования инструкциям (JSON формат)
2. Отсутствие галлюцинаций (не придумывает несуществующее)
3. Скорость ответа
4. Качество рассуждений
5. Проактивность (спрашивает об аллергиях)
"""

import time
import json
from openai import OpenAI
from src.config import Config

# Модели для тестирования (актуальные на 2025)
MODELS_TO_TEST = [
    "meta-llama/llama-4-scout-17b-16e-instruct",    # Текущая (Preview)
    "llama-3.3-70b-versatile",                       # Production 70B
    "meta-llama/llama-4-maverick-17b-128e-instruct", # Preview - больше экспертов
    "llama-3.1-8b-instant",                          # Production - быстрая
    "qwen/qwen-3-32b",                               # Preview - Qwen 32B
    "moonshotai/kimi-k2-instruct-0905",              # Preview - 256K контекст
]

# Тестовые сценарии
TEST_SCENARIOS = [
    {
        "name": "Базовый диалог",
        "messages": [
            {"role": "user", "content": "Хочу пиццу"}
        ],
        "expected": {
            "should_ask_count": True,  # Должен спросить количество людей
            "should_be_text": True,    # Должен ответить текстом, не JSON
        }
    },
    {
        "name": "Запрос с количеством",
        "messages": [
            {"role": "user", "content": "Хочу пиццу"},
            {"role": "assistant", "content": "Сколько вас будет?"},
            {"role": "user", "content": "Нас 4 человека"}
        ],
        "expected": {
            "should_ask_allergies": True,  # Должен спросить об аллергиях
            "should_be_text": True,
        }
    },
    {
        "name": "Готов к действию",
        "messages": [
            {"role": "user", "content": "Хочу пиццу"},
            {"role": "assistant", "content": "Сколько вас будет?"},
            {"role": "user", "content": "Нас 4 человека"},
            {"role": "assistant", "content": "Есть ли у вас аллергии или продукты которые не едите?"},
            {"role": "user", "content": "Нет, всё едим"}
        ],
        "expected": {
            "should_be_json": True,        # Должен дать JSON действие
            "should_have_action": True,    # Должен содержать action
        }
    },
    {
        "name": "Анализ страницы (антигаллюцинация)",
        "messages": [
            {"role": "user", "content": "Результат выполнения действия. Что дальше?"}
        ],
        "context": """Действие: get_page_text
Статус: success

Текст страницы (начало):
Пепперони 599₽
Маргарита 449₽
Четыре сыра 649₽
Гавайская 549₽
Мясная 699₽

Пользователь хочет: пиццу с креветками""",
        "expected": {
            "should_not_hallucinate": True,  # НЕ должен придумывать "Креветочная пицца"
            "forbidden_words": ["креветочная пицца", "пицца с креветками"],
        }
    },
    {
        "name": "Проверка аллергий в составе",
        "messages": [
            {"role": "user", "content": "Результат выполнения действия. Что дальше?"}
        ],
        "context": """Действие: get_modal_text
Статус: success

Текст модального окна:
Пепперони
Состав: томатный соус, сыр моцарелла, пепперони, орегано
Цена: 599₽

⚠️ ОГРАНИЧЕНИЯ ПОЛЬЗОВАТЕЛЯ:
🚨 АЛЛЕРГИИ: помидоры""",
        "expected": {
            "should_reject_dish": True,  # Должен отказаться от блюда с томатами
            "should_mention_tomato": True,  # Должен упомянуть что есть томаты
        }
    }
]

# Системный промпт (сокращённый для тестов)
SYSTEM_PROMPT = """Ты - AI помощник для заказа еды на Додо Пицце.

ПРАВИЛА ДИАЛОГА:
1. ВСЕГДА спроси количество людей
2. ВСЕГДА спроси об аллергиях/ограничениях
3. Только потом начинай действия

ФОРМАТ ДЕЙСТВИЙ:
{"action": "navigate", "params": {"url": "..."}, "reasoning": "почему"}

КРИТИЧНО:
- НЕ придумывай несуществующие блюда
- Кликай ТОЛЬКО на то что видел в get_page_text
- Проверяй состав на аллергены пользователя
- Если есть аллерген - НЕ предлагай это блюдо

ДИАЛОГ = текст без JSON
ДЕЙСТВИЕ = только JSON
"""


def test_model(model_name: str) -> dict:
    """Протестировать одну модель"""
    print(f"\n{'='*60}")
    print(f"🧪 ТЕСТИРОВАНИЕ: {model_name}")
    print(f"{'='*60}")

    client = OpenAI(
        api_key=Config.get_api_key(),
        base_url=Config.get_base_url()
    )

    results = {
        "model": model_name,
        "tests": [],
        "total_time": 0,
        "passed": 0,
        "failed": 0,
        "errors": []
    }

    for scenario in TEST_SCENARIOS:
        print(f"\n📝 Тест: {scenario['name']}")

        test_result = {
            "name": scenario["name"],
            "passed": False,
            "response": "",
            "time": 0,
            "issues": []
        }

        try:
            # Формируем сообщения
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            messages.extend(scenario["messages"])

            # Добавляем контекст если есть
            if "context" in scenario:
                messages[-1]["content"] += f"\n\nКонтекст:\n{scenario['context']}"

            # Замеряем время
            start_time = time.time()

            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                max_tokens=500,
                temperature=0.7
            )

            elapsed = time.time() - start_time
            test_result["time"] = round(elapsed, 2)
            results["total_time"] += elapsed

            answer = response.choices[0].message.content.strip()
            test_result["response"] = answer[:200] + "..." if len(answer) > 200 else answer

            print(f"   ⏱️  Время: {test_result['time']}с")
            print(f"   💬 Ответ: {test_result['response'][:100]}...")

            # Проверяем ожидания
            expected = scenario["expected"]
            passed = True

            # Проверка: должен спросить количество
            if expected.get("should_ask_count"):
                if not any(w in answer.lower() for w in ["сколько", "человек", "количество"]):
                    test_result["issues"].append("Не спросил количество людей")
                    passed = False

            # Проверка: должен спросить об аллергиях
            if expected.get("should_ask_allergies"):
                if not any(w in answer.lower() for w in ["аллерг", "не едите", "ограничен", "непереносим"]):
                    test_result["issues"].append("Не спросил об аллергиях")
                    passed = False

            # Проверка: должен быть текст (не JSON)
            if expected.get("should_be_text"):
                if answer.strip().startswith("{"):
                    test_result["issues"].append("Дал JSON вместо текста")
                    passed = False

            # Проверка: должен быть JSON
            if expected.get("should_be_json"):
                if not "{" in answer:
                    test_result["issues"].append("Не дал JSON действие")
                    passed = False

            # Проверка: должен содержать action
            if expected.get("should_have_action"):
                if '"action"' not in answer:
                    test_result["issues"].append("JSON не содержит action")
                    passed = False

            # Проверка: не должен галлюцинировать
            if expected.get("should_not_hallucinate"):
                forbidden = expected.get("forbidden_words", [])
                for word in forbidden:
                    if word.lower() in answer.lower():
                        test_result["issues"].append(f"Галлюцинация: '{word}'")
                        passed = False

            # Проверка: должен отказаться от блюда
            if expected.get("should_reject_dish"):
                reject_words = ["не подходит", "нельзя", "аллерг", "томат", "помидор", "другое", "ищу дальше"]
                if not any(w in answer.lower() for w in reject_words):
                    test_result["issues"].append("Не отказался от блюда с аллергеном")
                    passed = False

            test_result["passed"] = passed

            if passed:
                print(f"   ✅ PASSED")
                results["passed"] += 1
            else:
                print(f"   ❌ FAILED: {', '.join(test_result['issues'])}")
                results["failed"] += 1

        except Exception as e:
            print(f"   ❌ ERROR: {str(e)}")
            test_result["issues"].append(f"Error: {str(e)}")
            results["failed"] += 1
            results["errors"].append(str(e))

        results["tests"].append(test_result)

    return results


def run_comparison():
    """Запустить сравнение всех моделей"""
    print("\n" + "="*70)
    print("🔬 СРАВНЕНИЕ МОДЕЛЕЙ GROQ ДЛЯ AI АГЕНТА")
    print("="*70)

    all_results = []

    for model in MODELS_TO_TEST:
        try:
            result = test_model(model)
            all_results.append(result)
        except Exception as e:
            print(f"\n❌ Не удалось протестировать {model}: {e}")
            all_results.append({
                "model": model,
                "error": str(e),
                "passed": 0,
                "failed": len(TEST_SCENARIOS),
                "total_time": 0
            })

    # Итоговая таблица
    print("\n" + "="*70)
    print("📊 ИТОГОВЫЕ РЕЗУЛЬТАТЫ")
    print("="*70)

    print(f"\n{'Модель':<45} {'Passed':<8} {'Failed':<8} {'Время':<10}")
    print("-"*70)

    best_model = None
    best_score = -1

    for result in all_results:
        model = result["model"]
        passed = result.get("passed", 0)
        failed = result.get("failed", 0)
        total_time = result.get("total_time", 0)

        # Короткое имя модели
        short_name = model.split("/")[-1] if "/" in model else model

        print(f"{short_name:<45} {passed:<8} {failed:<8} {total_time:.2f}s")

        # Определяем лучшую модель (по количеству passed, при равенстве - по скорости)
        score = passed * 1000 - total_time  # passed важнее скорости
        if score > best_score:
            best_score = score
            best_model = model

    print("-"*70)

    if best_model:
        print(f"\n🏆 ЛУЧШАЯ МОДЕЛЬ: {best_model}")

    # Сохраняем результаты в файл
    with open("model_comparison_results.json", "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    print(f"\n📁 Результаты сохранены в model_comparison_results.json")

    return all_results


if __name__ == "__main__":
    run_comparison()
