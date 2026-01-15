import asyncio
from playwright.async_api import async_playwright, Page, Browser
from typing import Optional, Dict, Any
import json
from datetime import datetime

class BrowserTools:
    """Инструменты для управления браузером"""
    
    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.context = None
        
    async def start_browser(self, headless: bool = False) -> Dict[str, Any]:
        """Запустить браузер с антидетект настройками"""
        try:
            self.playwright = await async_playwright().start()

            self.browser = await self.playwright.firefox.launch(
                headless=headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox'
                ]
            )

            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                locale='ru-RU',
                timezone_id='Asia/Krasnoyarsk',
                geolocation={'latitude': 56.0153, 'longitude': 92.8932},
                permissions=['geolocation']
            )

            await self.context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """)

            self.page = await self.context.new_page()

            return {
                "status": "success",
                "message": "Браузер запущен"
            }
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)

            # Специфичные сообщения для разных типов ошибок
            if "Executable doesn't exist" in error_msg or "firefox" in error_msg.lower():
                return {
                    "status": "error",
                    "message": (
                        f"Не удалось запустить Firefox браузер.\n"
                        f"Причина: {error_msg}\n\n"
                        f"Решение:\n"
                        f"1. Установите Firefox для Playwright командой:\n"
                        f"   playwright install firefox\n"
                        f"2. Или установите все браузеры:\n"
                        f"   playwright install"
                    )
                }
            elif "timeout" in error_msg.lower():
                return {
                    "status": "error",
                    "message": (
                        f"Превышено время ожидания запуска браузера ({error_type}).\n"
                        f"Возможные причины:\n"
                        f"- Недостаточно системных ресурсов\n"
                        f"- Браузер заблокирован антивирусом\n"
                        f"- Проблемы с правами доступа\n\n"
                        f"Попробуйте:\n"
                        f"1. Закрыть другие приложения\n"
                        f"2. Переустановить браузер: playwright install firefox"
                    )
                }
            else:
                return {
                    "status": "error",
                    "message": (
                        f"Не удалось запустить браузер ({error_type}).\n"
                        f"Ошибка: {error_msg}\n\n"
                        f"Попробуйте:\n"
                        f"1. Переустановить браузер: playwright install firefox\n"
                        f"2. Проверить системные требования\n"
                        f"3. Обратиться к разделу Troubleshooting в README.md"
                    )
                }
    
    async def navigate(self, url: str) -> Dict[str, Any]:
        """Перейти по URL"""
        try:
            await self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(2)

            return {
                "status": "success",
                "message": f"Перешли на {url}",
                "url": self.page.url,
                "title": await self.page.title()
            }
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)

            if "timeout" in error_msg.lower():
                return {
                    "status": "error",
                    "message": (
                        f"Не удалось загрузить страницу {url} (превышен таймаут).\n"
                        f"Возможные причины:\n"
                        f"- Медленное интернет-соединение\n"
                        f"- Сайт недоступен или перегружен\n"
                        f"- Проблемы с сетью\n\n"
                        f"Попробуйте:\n"
                        f"1. Проверить интернет-соединение\n"
                        f"2. Открыть {url} в обычном браузере\n"
                        f"3. Повторить попытку позже"
                    )
                }
            elif "net::" in error_msg.lower() or "dns" in error_msg.lower():
                return {
                    "status": "error",
                    "message": (
                        f"Не удалось подключиться к {url} (сетевая ошибка).\n"
                        f"Причина: {error_msg}\n\n"
                        f"Возможные причины:\n"
                        f"- Неверный URL адрес\n"
                        f"- Сайт недоступен\n"
                        f"- Проблемы с DNS\n\n"
                        f"Проверьте правильность URL и доступность сайта."
                    )
                }
            else:
                return {
                    "status": "error",
                    "message": (
                        f"Ошибка при переходе на {url} ({error_type}).\n"
                        f"Детали: {error_msg}"
                    )
                }
    
    async def click(self, selector: str) -> Dict[str, Any]:
        """Кликнуть по элементу"""
        try:
            await self.page.click(selector, timeout=10000)
            await asyncio.sleep(1)

            return {
                "status": "success",
                "message": f"Кликнули по {selector}"
            }
        except Exception as e:
            error_msg = str(e)

            if "timeout" in error_msg.lower() or "not visible" in error_msg.lower():
                return {
                    "status": "error",
                    "message": (
                        f"Не удалось кликнуть по элементу '{selector}' (элемент не найден или не виден).\n"
                        f"Возможные причины:\n"
                        f"- Элемент ещё не загрузился\n"
                        f"- Элемент скрыт другим элементом\n"
                        f"- Неверный селектор\n\n"
                        f"Попробуйте подождать загрузки страницы или использовать другой селектор."
                    )
                }
            elif "strict mode violation" in error_msg.lower():
                return {
                    "status": "error",
                    "message": (
                        f"Найдено несколько элементов с селектором '{selector}'.\n"
                        f"Уточните селектор, чтобы выбрать конкретный элемент."
                    )
                }
            else:
                return {
                    "status": "error",
                    "message": f"Ошибка клика по '{selector}': {error_msg}"
                }
    
    async def type_text(self, selector: str, text: str) -> Dict[str, Any]:
        """Ввести текст в поле"""
        try:
            await self.page.fill(selector, text)
            await asyncio.sleep(0.5)
            
            return {
                "status": "success",
                "message": f"Ввели текст '{text}' в {selector}"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Ошибка ввода текста: {str(e)}"
            }
    
    async def take_screenshot(self, filename: Optional[str] = None) -> Dict[str, Any]:
        """Сделать скриншот"""
        try:
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"screenshots/screenshot_{timestamp}.png"
            
            # Без full_page чтобы избежать ошибки с большими страницами
            await self.page.screenshot(path=filename)
            
            return {
                "status": "success",
                "message": f"Скриншот сохранён: {filename}",
                "path": filename
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Ошибка скриншота: {str(e)}"
            }
    
    async def get_page_text(self) -> Dict[str, Any]:
        """Получить текст страницы"""
        try:
            text = await self.page.inner_text('body')
            
            return {
                "status": "success",
                "text": text,
                "full_length": len(text)
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Ошибка получения текста: {str(e)}",
                "text": "",
                "full_length": 0
            }
    
    async def wait_for_element(self, selector: str, timeout: int = 10000) -> Dict[str, Any]:
        """Ждать появления элемента"""
        try:
            await self.page.wait_for_selector(selector, timeout=timeout)
            
            return {
                "status": "success",
                "message": f"Элемент {selector} появился"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Элемент не появился: {str(e)}"
            }

    async def click_by_text(self, text: str, exact: bool = False) -> Dict[str, Any]:
        """Кликнуть по элементу с определённым текстом"""
        try:
            locator = self.page.get_by_text(text, exact=True) if exact else self.page.get_by_text(text).first

            # Попытка 1: Обычный клик
            try:
                await locator.click(timeout=5000)
                await asyncio.sleep(1)
                return {
                    "status": "success",
                    "message": f"Кликнули по '{text}'"
                }
            except Exception as first_error:
                # Попытка 2: Закрыть возможные модальные окна и повторить
                try:
                    # Закрываем popup если есть
                    await self.page.keyboard.press("Escape")
                    await asyncio.sleep(0.5)

                    # Пытаемся кликнуть снова
                    await locator.click(timeout=5000)
                    await asyncio.sleep(1)
                    return {
                        "status": "success",
                        "message": f"Кликнули по '{text}' (после закрытия popup)"
                    }
                except Exception as second_error:
                    # Попытка 3: Force click
                    try:
                        await locator.click(force=True, timeout=5000)
                        await asyncio.sleep(1)
                        return {
                            "status": "success",
                            "message": f"Кликнули по '{text}' (force)"
                        }
                    except Exception as final_error:
                        # Все попытки провалились
                        raise final_error

        except Exception as e:
            return {
                "status": "error",
                "message": f"Ошибка клика по тексту: {str(e)}"
            }
    
    async def click_by_text_force(self, text: str) -> Dict[str, Any]:
        """Кликнуть по элементу с текстом (принудительно)"""
        try:
            await self.page.get_by_text(text).first.click(force=True, timeout=10000)
            await asyncio.sleep(1)
            
            return {
                "status": "success",
                "message": f"Кликнули по '{text}' (force)"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Ошибка клика: {str(e)}"
            }
    
    async def wait_for_text(self, text: str, timeout: int = 10000) -> Dict[str, Any]:
        """Ждать появления текста на странице"""
        try:
            await self.page.get_by_text(text).first.wait_for(timeout=timeout)
            
            return {
                "status": "success",
                "message": f"Текст '{text}' появился"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Текст не появился: {str(e)}"
            }
    
    async def press_key(self, key: str) -> Dict[str, Any]:
        """Нажать клавишу"""
        try:
            await self.page.keyboard.press(key)
            await asyncio.sleep(0.5)
            
            return {
                "status": "success",
                "message": f"Нажата клавиша '{key}'"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Ошибка нажатия клавиши: {str(e)}"
            }
    
    async def scroll_down(self, pixels: int = 500) -> Dict[str, Any]:
        """Прокрутить страницу вниз"""
        try:
            await self.page.evaluate(f"window.scrollBy(0, {pixels})")
            await asyncio.sleep(0.5)

            return {
                "status": "success",
                "message": f"Прокрутили на {pixels}px вниз"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Ошибка прокрутки: {str(e)}"
            }

    async def scroll_up(self, pixels: int = 500) -> Dict[str, Any]:
        """Прокрутить страницу вверх"""
        try:
            await self.page.evaluate(f"window.scrollBy(0, -{pixels})")
            await asyncio.sleep(0.5)

            return {
                "status": "success",
                "message": f"Прокрутили на {pixels}px вверх"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Ошибка прокрутки: {str(e)}"
            }

    async def press_key(self, key: str) -> Dict[str, Any]:
        """Нажать клавишу (Enter, Escape, Tab, и т.д.)"""
        try:
            await self.page.keyboard.press(key)
            await asyncio.sleep(0.3)

            return {
                "status": "success",
                "message": f"Нажата клавиша {key}"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Ошибка нажатия клавиши: {str(e)}"
            }

    async def find_text_on_page(self, search_text: str) -> Dict[str, Any]:
        """
        Найти текст на странице (Ctrl+F поиск)
        Использует браузерный поиск по странице
        """
        try:
            # Открываем поиск через Ctrl+F
            await self.page.keyboard.press('Control+F')
            await asyncio.sleep(0.5)

            # Вводим текст в поисковое поле браузера
            await self.page.keyboard.type(search_text)
            await asyncio.sleep(1)

            # Проверяем, есть ли текст на странице
            elements = await self.page.get_by_text(search_text, exact=False).all()
            found_count = len(elements)

            # Закрываем поиск
            await self.page.keyboard.press('Escape')
            await asyncio.sleep(0.3)

            if found_count > 0:
                return {
                    "status": "success",
                    "message": f"Найдено совпадений: {found_count}",
                    "count": found_count,
                    "found": True
                }
            else:
                return {
                    "status": "success",
                    "message": "Текст не найден на странице",
                    "count": 0,
                    "found": False
                }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Ошибка поиска: {str(e)}",
                "found": False
            }
    
    async def get_menu_items(self) -> Dict[str, Any]:
        """Получить список позиций меню (для Додо Пиццы)"""
        try:
            items = []
            
            # Находим все карточки товаров
            cards = await self.page.locator('article').all()
            
            for card in cards[:15]:  # первые 15 для теста
                try:
                    # Извлекаем название и цену
                    title_elem = card.locator('h3, h2').first
                    price_elem = card.locator('[class*="price"]').first
                    
                    title = await title_elem.inner_text() if await title_elem.count() > 0 else "Без названия"
                    price = await price_elem.inner_text() if await price_elem.count() > 0 else "?"
                    
                    items.append({
                        "title": title.strip(),
                        "price": price.strip()
                    })
                except:
                    continue
            
            return {
                "status": "success",
                "items": items,
                "count": len(items)
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Ошибка парсинга меню: {str(e)}",
                "items": [],
                "count": 0
            }

    async def close_modal(self) -> Dict[str, Any]:
        """
        Закрыть модальное окно
        Пробует несколько способов: Escape, клик по overlay, кнопка закрытия
        """
        try:
            # Способ 1: Escape - самый универсальный
            await self.page.keyboard.press('Escape')
            await asyncio.sleep(0.5)

            # Проверяем, закрылось ли окно
            # Ищем типичные селекторы модальных окон
            modal_selectors = [
                '[role="dialog"]',
                '[class*="modal"]',
                '[class*="Modal"]',
                '[class*="popup"]',
                '[class*="overlay"]'
            ]

            modal_still_open = False
            for selector in modal_selectors:
                elements = await self.page.locator(selector).all()
                if len(elements) > 0:
                    # Проверяем видимость
                    for elem in elements:
                        if await elem.is_visible():
                            modal_still_open = True
                            break
                if modal_still_open:
                    break

            if not modal_still_open:
                return {
                    "status": "success",
                    "message": "Модальное окно закрыто (Escape)",
                    "method": "escape"
                }

            # Способ 2: Кнопка закрытия
            close_button_selectors = [
                'button[aria-label*="закрыть"]',
                'button[aria-label*="Закрыть"]',
                'button[aria-label*="close"]',
                'button[aria-label*="Close"]',
                '[class*="close"]',
                '[class*="Close"]',
                'button:has-text("✕")',
                'button:has-text("×")'
            ]

            for selector in close_button_selectors:
                try:
                    element = self.page.locator(selector).first
                    if await element.is_visible():
                        await element.click(timeout=2000)
                        await asyncio.sleep(0.5)
                        return {
                            "status": "success",
                            "message": "Модальное окно закрыто (кнопка)",
                            "method": "button"
                        }
                except:
                    continue

            # Способ 3: Клик вне модального окна (по overlay)
            try:
                overlay = self.page.locator('[class*="overlay"]').first
                if await overlay.is_visible():
                    # Кликаем в угол overlay
                    box = await overlay.bounding_box()
                    if box:
                        await self.page.mouse.click(box['x'] + 10, box['y'] + 10)
                        await asyncio.sleep(0.5)
                        return {
                            "status": "success",
                            "message": "Модальное окно закрыто (клик по overlay)",
                            "method": "overlay"
                        }
            except:
                pass

            return {
                "status": "warning",
                "message": "Модальное окно может быть ещё открыто, но попытки закрытия выполнены"
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Ошибка закрытия модального окна: {str(e)}"
            }

    async def wait_for_modal(self, timeout: int = 5000) -> Dict[str, Any]:
        """
        Подождать появления модального окна
        """
        try:
            modal_selectors = [
                '[role="dialog"]',
                '[class*="modal"]',
                '[class*="Modal"]',
                '[class*="popup"]'
            ]

            for selector in modal_selectors:
                try:
                    await self.page.wait_for_selector(selector, timeout=timeout, state='visible')
                    return {
                        "status": "success",
                        "message": "Модальное окно появилось",
                        "selector": selector
                    }
                except:
                    continue

            return {
                "status": "timeout",
                "message": "Модальное окно не появилось"
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Ошибка ожидания модального окна: {str(e)}"
            }

    async def get_modal_text(self) -> Dict[str, Any]:
        """
        Получить текст из модального окна
        """
        try:
            # Даём время на загрузку содержимого модального окна
            await asyncio.sleep(0.5)

            modal_selectors = [
                '[role="dialog"]',
                '[class*="modal"]',
                '[class*="Modal"]',
                '[class*="popup"]',
                '[class*="Popup"]'
            ]

            for selector in modal_selectors:
                try:
                    elements = await self.page.locator(selector).all()
                    for modal in elements:
                        if await modal.is_visible():
                            # Ждём немного для полной загрузки контента
                            await asyncio.sleep(0.3)
                            text = await modal.inner_text()

                            # Если текст пустой, попробуем через textContent
                            if not text or len(text) < 10:
                                text = await modal.text_content()

                            if text and len(text) > 0:
                                return {
                                    "status": "success",
                                    "text": text,
                                    "length": len(text),
                                    "selector": selector
                                }
                except Exception as e:
                    continue

            return {
                "status": "error",
                "message": "Модальное окно не найдено или пустое"
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Ошибка чтения модального окна: {str(e)}"
            }

    async def close_browser(self) -> Dict[str, Any]:
        """Закрыть браузер"""
        try:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            
            return {
                "status": "success",
                "message": "Браузер закрыт"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Ошибка закрытия: {str(e)}"
            }