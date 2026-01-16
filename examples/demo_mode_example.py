#!/usr/bin/env python3
"""
Пример использования Demo Mode.

Демонстрирует:
- Логирование выполнения функций
- Визуальные маркеры в браузере
- Задержки между действиями
- Показ выполняемого кода

Использование:
    # Обычный режим
    python examples/demo_mode_example.py

    # Demo Mode
    python examples/demo_mode_example.py --demo
"""
import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию в path
sys.path.insert(0, str(Path(__file__).parent.parent))

from playwright.async_api import async_playwright
from src.utils.demo_mode import demo_async_action, initialize_demo_mode, get_demo_mode
from src.utils.visual_markers import get_visual_markers


@demo_async_action
async def open_website(page, url: str):
    """Открыть веб-сайт"""
    demo = get_demo_mode()
    markers = get_visual_markers(page, enabled=demo.enabled)

    if demo.enabled:
        await markers.show_action_indicator(f"Открытие {url}", duration=2000)

    await page.goto(url)
    await page.wait_for_load_state("networkidle")


@demo_async_action
async def search_text(page, query: str):
    """Поиск текста на странице"""
    demo = get_demo_mode()
    markers = get_visual_markers(page, enabled=demo.enabled)

    # Находим поисковое поле
    search_input = page.locator("input[type='search'], input[name='q'], input[placeholder*='Search']").first

    if demo.enabled:
        await markers.show_action_indicator(f"Поиск: {query}", duration=2000)
        await markers.show_typing("input", duration=1500)

    await search_input.fill(query)

    if demo.enabled:
        await demo.delay("after_action")


@demo_async_action
async def click_element(page, text: str):
    """Кликнуть по элементу с текстом"""
    demo = get_demo_mode()
    markers = get_visual_markers(page, enabled=demo.enabled)

    if demo.enabled:
        await markers.show_action_indicator(f"Клик по: {text}", duration=2000)
        await markers.highlight_click_by_text(text, duration=800)

    await page.click(f"text={text}")

    if demo.enabled:
        await demo.delay("after_action")


@demo_async_action
async def scroll_page(page, direction: str = "down", pixels: int = 500):
    """Прокрутить страницу"""
    demo = get_demo_mode()
    markers = get_visual_markers(page, enabled=demo.enabled)

    if demo.enabled:
        await markers.show_scroll_indicator(direction, duration=1000)

    if direction == "down":
        await page.mouse.wheel(0, pixels)
    else:
        await page.mouse.wheel(0, -pixels)

    if demo.enabled:
        await demo.delay("after_action")


async def demo_scenario(headless: bool = False):
    """
    Демонстрационный сценарий.

    Выполняет последовательность действий на тестовом сайте.
    """
    demo = get_demo_mode()

    print("\n" + "="*70)
    print("🎬 ДЕМОНСТРАЦИОННЫЙ СЦЕНАРИЙ")
    print("="*70)

    if demo.enabled:
        print("✅ Demo Mode: ВКЛЮЧЕН")
        print(f"   Задержки: {demo.config.delays}")
        print(f"   Визуальные маркеры: {demo.config.visual_markers_enabled}")
    else:
        print("⏸️  Demo Mode: ВЫКЛЮЧЕН (обычный режим)")

    print("="*70 + "\n")

    async with async_playwright() as p:
        # Запускаем браузер
        browser = await p.firefox.launch(headless=headless)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # Шаг 1: Открываем сайт Wikipedia
            print("\n📍 Шаг 1: Открытие Wikipedia")
            await open_website(page, "https://www.wikipedia.org")

            # Шаг 2: Вводим запрос
            print("\n📍 Шаг 2: Поиск информации об искусственном интеллекте")
            await search_text(page, "Artificial Intelligence")

            # Шаг 3: Кликаем по кнопке поиска (если есть)
            print("\n📍 Шаг 3: Нажатие кнопки поиска")
            try:
                # Нажимаем Enter вместо клика
                await page.keyboard.press("Enter")
                await page.wait_for_load_state("networkidle")
            except Exception as e:
                print(f"   ⚠️  Поиск через Enter не сработал: {e}")

            # Шаг 4: Скроллим вниз
            print("\n📍 Шаг 4: Прокрутка страницы вниз")
            await scroll_page(page, "down", 500)

            # Шаг 5: Ещё скролл
            print("\n📍 Шаг 5: Ещё прокрутка")
            await scroll_page(page, "down", 500)

            # Шаг 6: Скролл вверх
            print("\n📍 Шаг 6: Прокрутка обратно вверх")
            await scroll_page(page, "up", 300)

            print("\n" + "="*70)
            print("✅ СЦЕНАРИЙ ЗАВЕРШЁН")
            print("="*70 + "\n")

            # Пауза перед закрытием
            if demo.enabled:
                print("⏸️  Пауза перед закрытием браузера...")
                await asyncio.sleep(3)

        except Exception as e:
            print(f"\n❌ Ошибка: {e}")
            raise

        finally:
            # Очистка
            markers = get_visual_markers(page, enabled=demo.enabled)
            await markers.cleanup()
            await browser.close()


def main():
    """Главная функция"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Демонстрация Demo Mode для AI Browser Agent"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Включить Demo Mode"
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Запустить браузер в headless режиме"
    )

    args = parser.parse_args()

    # Инициализация demo mode
    if args.demo:
        initialize_demo_mode(enabled=True)

    # Запуск сценария
    asyncio.run(demo_scenario(headless=args.headless))


if __name__ == "__main__":
    main()
