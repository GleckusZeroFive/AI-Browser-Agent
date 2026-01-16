"""
Интеграционный тест: полный флоу заказа еды с оптимизацией контекста
"""
import pytest
import asyncio
from src.dialogue_manager import DialogueManager


@pytest.mark.asyncio
@pytest.mark.integration
async def test_shopping_full_flow():
    """
    Тест полного сценария заказа еды с проверкой оптимизации контекста
    """
    manager = DialogueManager()

    # Шаг 1: Первый запрос (должен использовать COMPACT или FULL)
    await manager._process_user_input("Хочу заказать пиццу")

    stats1 = manager.agent.get_token_usage_stats()
    assert stats1['context_level'] in ['compact', 'full']
    assert stats1['used_tokens'] < stats1['safe_limit']

    # Шаг 2: Добавляем контекст
    for i in range(10):
        await manager._process_user_input(f"Дополнительная информация {i}")

    # Шаг 3: Большой контекст - должен сократиться до MINIMAL
    await manager._process_user_input("Покажи варианты пиццы")

    stats2 = manager.agent.get_token_usage_stats()

    # Проверки
    assert stats2['context_level'] in ['minimal', 'compact']
    assert manager.agent.rate_limit_count == 0, "Не должно быть rate limit ошибок"
    assert stats2['used_tokens'] < stats2['safe_limit']

    print("\n✅ Интеграционный тест прошёл успешно!")
    print(f"   Финальный уровень: {stats2['context_level']}")
    print(f"   Экономия: {stats2['kb_savings_percent']}%")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_context_degradation():
    """
    Тест graceful degradation: FULL → COMPACT → MINIMAL
    """
    manager = DialogueManager()

    levels_observed = []

    # Постепенно заполняем контекст
    for i in range(25):
        await manager._process_user_input(f"Сообщение {i}")

        stats = manager.agent.get_token_usage_stats()
        level = stats['context_level']

        if not levels_observed or levels_observed[-1] != level:
            levels_observed.append(level)
            print(f"Iteration {i}: уровень изменился на {level}")

    # Должны были пройти FULL/COMPACT → MINIMAL
    assert 'minimal' in levels_observed, "Должен был переключиться на MINIMAL"
    assert len(levels_observed) >= 2, "Должно быть хотя бы 2 уровня"

    print(f"\n✅ Graceful degradation работает: {' → '.join(levels_observed)}")


def run_integration_tests():
    """Запуск интеграционных тестов"""
    pytest.main([__file__, "-v", "-m", "integration", "--tb=short"])


if __name__ == "__main__":
    asyncio.run(test_shopping_full_flow())
    asyncio.run(test_context_degradation())
