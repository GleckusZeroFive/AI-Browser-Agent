"""
Полное исследование сайта Додо Пиццы
Цель: изучить структуру, селекторы, flow заказа
"""
import asyncio
import json
from datetime import datetime
from src.tools.browser_tools import BrowserTools

class DodoPizzaResearcher:
    """Исследователь сайта Додо Пиццы"""

    def __init__(self):
        self.tools = BrowserTools()
        self.findings = {
            "timestamp": datetime.now().isoformat(),
            "url": "https://dodopizza.ru/krasnoyarsk",
            "structure": {},
            "selectors": {},
            "flows": {},
            "menu_items": [],
            "errors": []
        }

    async def research(self):
        """Основной метод исследования"""
        print("="*60)
        print("ИССЛЕДОВАНИЕ САЙТА ДОДО ПИЦЦЫ")
        print("="*60)

        try:
            # 1. Запуск браузера
            await self._step_1_launch()

            # 2. Анализ главной страницы
            await self._step_2_main_page()

            # 3. Анализ структуры меню
            await self._step_3_menu_structure()

            # 4. Тест открытия карточки товара
            await self._step_4_product_card()

            # 5. Тест добавления в корзину
            await self._step_5_add_to_cart()

            # 6. Исследование модальных окон
            await self._step_6_modals()

        except Exception as e:
            self.findings["errors"].append({
                "stage": "general",
                "error": str(e)
            })
            print(f"\n❌ Критическая ошибка: {e}")

        finally:
            # Сохраняем результаты
            await self._save_findings()

            # Закрываем браузер
            print("\n🔒 Закрываем браузер...")
            await self.tools.close_browser()

            print("\n" + "="*60)
            print("ИССЛЕДОВАНИЕ ЗАВЕРШЕНО")
            print("="*60)
            print(f"\n📊 Результаты сохранены в: logs/research_results.json")
            print(f"📸 Скриншоты в: screenshots/research_*.png")

    async def _step_1_launch(self):
        """Шаг 1: Запуск браузера"""
        print("\n📍 ШАГ 1: Запуск браузера")
        print("-" * 60)

        result = await self.tools.start_browser(headless=False)
        print(f"✓ Статус: {result['status']}")

        if result['status'] == 'error':
            raise Exception(f"Не удалось запустить браузер: {result['message']}")

    async def _step_2_main_page(self):
        """Шаг 2: Анализ главной страницы"""
        print("\n📍 ШАГ 2: Анализ главной страницы")
        print("-" * 60)

        # Переход на сайт
        print("🌐 Открываем dodopizza.ru...")
        result = await self.tools.navigate("https://dodopizza.ru/krasnoyarsk")
        print(f"✓ URL: {result.get('url')}")
        print(f"✓ Title: {result.get('title')}")

        self.findings["structure"]["url"] = result.get('url')
        self.findings["structure"]["title"] = result.get('title')

        # Ждём загрузки
        print("\n⏳ Ждём полной загрузки страницы (5 сек)...")
        await asyncio.sleep(5)

        # Скриншот
        print("📸 Делаем скриншот главной страницы...")
        await self.tools.take_screenshot("screenshots/research_01_main.png")

        # Получаем текст
        print("📝 Извлекаем текст страницы...")
        text_result = await self.tools.get_page_text()
        text_length = text_result.get('full_length', 0)
        print(f"✓ Длина текста: {text_length} символов")

        # Сохраняем текст
        with open("logs/research_main_page.txt", "w", encoding="utf-8") as f:
            f.write(text_result.get('text', ''))
        print("✓ Текст сохранён в logs/research_main_page.txt")

        self.findings["structure"]["main_page_text_length"] = text_length

    async def _step_3_menu_structure(self):
        """Шаг 3: Анализ структуры меню"""
        print("\n📍 ШАГ 3: Анализ структуры меню")
        print("-" * 60)

        # Получаем список товаров
        print("🍕 Парсим товары на странице...")
        menu_result = await self.tools.get_menu_items()

        if menu_result['status'] == 'success':
            items = menu_result.get('items', [])
            print(f"✓ Найдено товаров: {len(items)}")

            # Показываем первые 5
            print("\n📋 Первые 5 товаров:")
            for i, item in enumerate(items[:5], 1):
                print(f"  {i}. {item['title']} - {item['price']}")

            self.findings["menu_items"] = items
            self.findings["structure"]["menu_items_count"] = len(items)
        else:
            print(f"❌ Ошибка парсинга меню: {menu_result.get('message')}")
            self.findings["errors"].append({
                "stage": "menu_parsing",
                "error": menu_result.get('message')
            })

    async def _step_4_product_card(self):
        """Шаг 4: Тест открытия карточки товара"""
        print("\n📍 ШАГ 4: Открытие карточки товара")
        print("-" * 60)

        # Пробуем кликнуть на первую пиццу
        test_items = ["2 пиццы", "Пепперони", "Маргарита"]

        for item_name in test_items:
            print(f"\n🔍 Пробуем кликнуть на '{item_name}'...")
            result = await self.tools.click_by_text(item_name)

            if result['status'] == 'success':
                print(f"✓ Успешно кликнули на '{item_name}'")

                # Ждём открытия
                await asyncio.sleep(2)

                # Скриншот
                filename = f"screenshots/research_02_product_{item_name.replace(' ', '_')}.png"
                await self.tools.take_screenshot(filename)
                print(f"📸 Скриншот: {filename}")

                # Сохраняем информацию
                self.findings["selectors"]["clickable_product"] = item_name

                # Получаем текст модалки
                modal_text_result = await self.tools.get_page_text()
                with open(f"logs/research_modal_{item_name.replace(' ', '_')}.txt", "w", encoding="utf-8") as f:
                    f.write(modal_text_result.get('text', ''))

                print(f"✓ Нашли рабочий товар: '{item_name}'")
                break
            else:
                print(f"❌ Не удалось кликнуть: {result.get('message')}")

        # Закрываем модалку (ESC)
        print("\n🔙 Закрываем модалку (ESC)...")
        await self.tools.press_key("Escape")
        await asyncio.sleep(1)

    async def _step_5_add_to_cart(self):
        """Шаг 5: Тест добавления в корзину"""
        print("\n📍 ШАГ 5: Добавление в корзину")
        print("-" * 60)

        # Открываем снова карточку
        product_name = self.findings["selectors"].get("clickable_product", "2 пиццы")
        print(f"🔍 Открываем '{product_name}'...")
        await self.tools.click_by_text(product_name)
        await asyncio.sleep(2)

        # Ищем кнопку "В корзину"
        print("🛒 Ищем кнопку 'В корзину'...")
        cart_buttons = ["В корзину", "Добавить в корзину", "Оформить"]

        for button_text in cart_buttons:
            print(f"  Пробуем: '{button_text}'")
            result = await self.tools.click_by_text_force(button_text)

            if result['status'] == 'success':
                print(f"✓ Нажали '{button_text}'")
                self.findings["selectors"]["cart_button"] = button_text

                await asyncio.sleep(3)

                # Скриншот после добавления
                await self.tools.take_screenshot("screenshots/research_03_after_cart.png")

                # Текст после добавления
                after_cart_result = await self.tools.get_page_text()
                with open("logs/research_after_cart.txt", "w", encoding="utf-8") as f:
                    f.write(after_cart_result.get('text', ''))

                print("✓ Товар добавлен в корзину")
                break

        print("\n⏳ Смотрим что произошло (5 сек)...")
        await asyncio.sleep(5)

    async def _step_6_modals(self):
        """Шаг 6: Исследование модальных окон"""
        print("\n📍 ШАГ 6: Исследование модальных окон")
        print("-" * 60)

        # Проверяем появился ли диалог доставки
        print("🔍 Проверяем появление диалога доставки...")

        delivery_texts = [
            "Указать адрес доставки",
            "Доставка",
            "Самовывоз",
            "Адрес"
        ]

        page_text_result = await self.tools.get_page_text()
        page_text = page_text_result.get('text', '')

        for text in delivery_texts:
            if text in page_text:
                print(f"✓ Найден текст: '{text}'")
                self.findings["flows"]["delivery_dialog_appears"] = True
                self.findings["selectors"]["delivery_option"] = text

        # Финальный скриншот
        await self.tools.take_screenshot("screenshots/research_04_final.png")

    async def _save_findings(self):
        """Сохранить результаты исследования"""
        print("\n💾 Сохраняем результаты...")

        with open("logs/research_results.json", "w", encoding="utf-8") as f:
            json.dump(self.findings, f, ensure_ascii=False, indent=2)

        print("✓ Результаты сохранены")

async def main():
    """Запуск исследования"""
    researcher = DodoPizzaResearcher()
    await researcher.research()

if __name__ == "__main__":
    asyncio.run(main())
