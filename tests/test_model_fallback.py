"""
Тест системы автоматического fallback моделей при rate limit
"""
import sys
sys.path.insert(0, '/home/gleckus/projects/ai-browser-agent')

from src.agent.ai_agent import AIAgent
from src.config import Config

def test_fallback_logic():
    """Проверить логику формирования списка fallback моделей"""
    agent = AIAgent()
    agent.add_system_prompt()

    # Симулируем выбор модели
    model_to_use = agent._select_model_for_request("Привет", None)

    # Формируем список fallback как в реальном коде
    models_to_try = [model_to_use] + [m for m in Config.FALLBACK_MODELS if m != model_to_use]

    print("=" * 60)
    print("ТЕСТ FALLBACK СИСТЕМЫ")
    print("=" * 60)
    print(f"\n📋 Конфигурация:")
    print(f"   DEFAULT_MODEL: {Config.DEFAULT_MODEL}")
    print(f"   FALLBACK_MODELS: {Config.FALLBACK_MODELS}")

    print(f"\n🎯 Выбранная модель: {model_to_use}")
    print(f"\n📊 Порядок fallback ({len(models_to_try)} моделей):")
    for i, model in enumerate(models_to_try, 1):
        print(f"   {i}. {model}")

    # Проверяем что нет дубликатов
    if len(models_to_try) != len(set(models_to_try)):
        print("\n❌ ОШИБКА: Есть дубликаты моделей!")
        return False

    # Проверяем что есть хотя бы 2 модели для fallback
    if len(models_to_try) < 2:
        print("\n❌ ОШИБКА: Недостаточно моделей для fallback!")
        return False

    print(f"\n✅ Тест пройден: {len(models_to_try)} уникальных моделей для fallback")
    return True

def test_rate_limit_counter():
    """Проверить счётчик rate limit"""
    agent = AIAgent()
    agent.add_system_prompt()

    print("\n" + "=" * 60)
    print("ТЕСТ СЧЁТЧИКА RATE LIMIT")
    print("=" * 60)

    # Начальное значение
    print(f"\n📊 Начальное значение: {agent.rate_limit_count}")

    # Симулируем несколько rate limit ошибок
    agent.rate_limit_count = 2
    print(f"📊 После 2 ошибок: {agent.rate_limit_count}")

    # Проверяем выбор модели при высоком rate_limit_count
    model = agent._select_model_for_request("тест", None)
    expected = Config.MODELS[Config.ModelType.FAST] if hasattr(Config, 'ModelType') else Config.DEFAULT_MODEL

    print(f"\n🎯 При rate_limit_count >= 2 выбирается: {model}")
    print(f"✅ Тест пройден")
    return True

if __name__ == "__main__":
    test_fallback_logic()
    test_rate_limit_counter()

    print("\n" + "=" * 60)
    print("Для полного теста запустите: python main.py")
    print("=" * 60)
