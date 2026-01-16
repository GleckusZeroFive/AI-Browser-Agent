import asyncio
from playwright.async_api import async_playwright, Page, Browser
from typing import Optional, Dict, Any
import json
from datetime import datetime
import random

# Импортируем обработчик капч
try:
    from src.utils.captcha_handler import CaptchaHandler, check_page_for_captcha
except ImportError:
    from utils.captcha_handler import CaptchaHandler, check_page_for_captcha

class BrowserTools:
    """Инструменты для управления браузером"""

    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.context = None
        self.captcha_handler: Optional[CaptchaHandler] = None
        self.auto_handle_captcha = True  # Автоматически обрабатывать капчи
        
    async def start_browser(self, headless: bool = False) -> Dict[str, Any]:
        """Запустить браузер с улучшенными антидетект настройками"""
        try:
            self.playwright = await async_playwright().start()

            # Более стелс аргументы для Firefox
            self.browser = await self.playwright.firefox.launch(
                headless=headless,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-web-security',
                    '--disable-features=IsolateOrigins,site-per-process'
                ],
                firefox_user_prefs={
                    # Отключаем WebDriver флаги
                    'dom.webdriver.enabled': False,
                    'useAutomationExtension': False,
                    # Включаем JavaScript
                    'javascript.enabled': True,
                    # Разрешаем canvas fingerprinting (чтобы не выглядеть подозрительно)
                    'privacy.resistFingerprinting': False,
                    # Cookies
                    'network.cookie.cookieBehavior': 0,
                }
            )

            # Генерируем более реалистичный viewport
            viewport_width = random.choice([1920, 1366, 1536, 1440])
            viewport_height = random.choice([1080, 768, 864, 900])

            # Реалистичный User-Agent
            user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            ]

            self.context = await self.browser.new_context(
                viewport={'width': viewport_width, 'height': viewport_height},
                user_agent=random.choice(user_agents),
                locale='ru-RU',
                timezone_id='Europe/Moscow',
                geolocation={'latitude': 55.7558, 'longitude': 37.6173},  # Москва
                permissions=['geolocation'],
                # Добавляем реалистичные headers
                extra_http_headers={
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                    'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1',
                    'Cache-Control': 'max-age=0'
                }
            )

            # Расширенный антидетект скрипт
            await self.context.add_init_script("""
                // Удаляем webdriver флаг
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });

                // Переопределяем permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );

                // Добавляем реалистичные плагины
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [
                        {
                            0: {type: "application/x-google-chrome-pdf", suffixes: "pdf", description: "Portable Document Format"},
                            description: "Portable Document Format",
                            filename: "internal-pdf-viewer",
                            length: 1,
                            name: "Chrome PDF Plugin"
                        },
                        {
                            0: {type: "application/pdf", suffixes: "pdf", description: "Portable Document Format"},
                            description: "Portable Document Format",
                            filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai",
                            length: 1,
                            name: "Chrome PDF Viewer"
                        }
                    ]
                });

                // Фиксим языки
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['ru-RU', 'ru', 'en-US', 'en']
                });

                // Canvas fingerprint protection
                const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
                HTMLCanvasElement.prototype.toDataURL = function(type) {
                    if (type === 'image/png' && this.width === 16 && this.height === 16) {
                        // Возвращаем слегка модифицированный результат
                        return originalToDataURL.apply(this, arguments);
                    }
                    return originalToDataURL.apply(this, arguments);
                };

                // WebGL fingerprint protection
                const getParameter = WebGLRenderingContext.prototype.getParameter;
                WebGLRenderingContext.prototype.getParameter = function(parameter) {
                    if (parameter === 37445) {
                        return 'Intel Inc.';
                    }
                    if (parameter === 37446) {
                        return 'Intel Iris OpenGL Engine';
                    }
                    return getParameter(parameter);
                };

                // Battery API (часто используется для детектирования)
                if ('getBattery' in navigator) {
                    navigator.getBattery = () => Promise.resolve({
                        charging: true,
                        chargingTime: 0,
                        dischargingTime: Infinity,
                        level: 1.0,
                        addEventListener: () => {},
                        removeEventListener: () => {},
                        dispatchEvent: () => true
                    });
                }

                // Реалистичный Chrome object
                window.chrome = {
                    runtime: {},
                    loadTimes: function() {},
                    csi: function() {},
                    app: {}
                };
            """)

            self.page = await self.context.new_page()

            # Инициализируем обработчик капч
            self.captcha_handler = CaptchaHandler(self.page)

            return {
                "status": "success",
                "message": "Браузер запущен с антидетект защитой"
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
        """Перейти по URL с автоматической проверкой капчи"""
        try:
            # Используем networkidle для более надежной загрузки динамического контента
            await self.page.goto(url, wait_until='networkidle', timeout=30000)
            # Дополнительное ожидание для React/Vue/AJAX приложений
            await asyncio.sleep(1.5)

            # Проверяем наличие капчи
            if self.auto_handle_captcha and self.captcha_handler:
                captcha_result = await self.captcha_handler.handle_captcha_if_present(
                    auto_wait=True,
                    timeout=300  # 5 минут на решение капчи
                )

                if captcha_result["captcha_detected"]:
                    if captcha_result["handled"]:
                        return {
                            "status": "success",
                            "message": f"Перешли на {url}. {captcha_result['message']}",
                            "url": self.page.url,
                            "title": await self.page.title(),
                            "captcha_encountered": True,
                            "captcha_solved": True
                        }
                    else:
                        return {
                            "status": "error",
                            "message": f"Капча не решена на {url}. {captcha_result['message']}",
                            "url": self.page.url,
                            "captcha_encountered": True,
                            "captcha_solved": False
                        }

            return {
                "status": "success",
                "message": f"Перешли на {url}",
                "url": self.page.url,
                "title": await self.page.title(),
                "captcha_encountered": False
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

    async def search_and_type(self, text: str) -> Dict[str, Any]:
        """
        Умный поиск: автоматически находит поле поиска и вводит текст.

        Перебирает типичные селекторы полей поиска на сайтах доставки еды
        и интернет-магазинах. Если стандартный селектор не работает,
        пробует альтернативные варианты.

        Args:
            text: текст для ввода в поле поиска

        Returns:
            Dict с результатом операции
        """
        # Типичные селекторы полей поиска (в порядке приоритета)
        search_selectors = [
            # Додопицца и другие сайты (из реального DOM)
            'input[placeholder*="Найти"]',
            'input[placeholder*="Искать"]',
            'input[aria-label*="Найти"]',
            'input[aria-label*="Искать"]',
            'input[role="combobox"]',

            # Стандартные атрибуты
            'input[type="search"]',
            'input[placeholder*="оиск"]',
            'input[placeholder*="скать"]',  # Искать
            'input[placeholder*="earch"]',
            'input[placeholder*="айти"]',  # Найти

            # ARIA атрибуты (высокий приоритет для React-приложений)
            '[role="searchbox"]',
            'input[aria-label*="оиск"]',
            'input[aria-label*="скать"]',
            'input[aria-label*="earch"]',

            # По классам (популярные паттерны)
            'input[class*="search"]',
            'input[class*="Search"]',
            '[class*="search"] input',
            '[class*="Search"] input',

            # По name/id
            'input[name*="search"]',
            'input[name*="query"]',
            'input[name*="q"]',
            'input[id*="search"]',
            '#search',

            # Data атрибуты (React/Vue компоненты)
            '[data-testid*="search"]',
            '[data-test*="search"]',
            '[data-qa*="search"]',

            # Специфичные для агрегаторов доставки
            'header input',
            'nav input',
            '[class*="header"] input',
            '[class*="Header"] input',
        ]

        tried_selectors = []
        errors = []

        for selector in search_selectors:
            tried_selectors.append(selector)
            try:
                # Пробуем найти элемент
                locator = self.page.locator(selector).first

                # Проверяем видимость с коротким таймаутом
                is_visible = await locator.is_visible(timeout=1500)
                if is_visible:
                    # Кликаем для фокуса
                    await locator.click(timeout=2000)
                    await asyncio.sleep(0.2)

                    # Очищаем поле перед вводом
                    await locator.fill('')
                    await asyncio.sleep(0.1)

                    # Вводим текст
                    await locator.fill(text)
                    await asyncio.sleep(0.3)

                    # Нажимаем Enter для запуска поиска
                    await self.page.keyboard.press('Enter')
                    await asyncio.sleep(1.5)

                    return {
                        "status": "success",
                        "message": f"Ввели '{text}' в поле поиска",
                        "selector_used": selector
                    }

            except Exception as e:
                errors.append(f"{selector}: {str(e)[:50]}")
                continue

        # Если ничего не нашли, пробуем клик по иконке/кнопке поиска
        search_buttons = [
            'button:has-text("Найти")',
            'button:has-text("Поиск")',
            'button:has-text("Search")',
            '[class*="search"] button',
            '[class*="search"] svg',
            'button[aria-label*="оиск"]',
        ]

        for btn_selector in search_buttons:
            try:
                btn = self.page.locator(btn_selector).first
                if await btn.is_visible(timeout=1000):
                    await btn.click(timeout=2000)
                    await asyncio.sleep(0.5)

                    # После клика должно появиться поле ввода
                    for selector in search_selectors[:10]:
                        try:
                            locator = self.page.locator(selector).first
                            if await locator.is_visible(timeout=1000):
                                await locator.fill(text)
                                await self.page.keyboard.press('Enter')
                                await asyncio.sleep(1.5)

                                return {
                                    "status": "success",
                                    "message": f"Ввели '{text}' в поле поиска (после клика по кнопке)",
                                    "selector_used": selector
                                }
                        except:
                            continue
            except:
                continue

        # Если поле поиска не найдено, используем браузерный поиск по странице (Ctrl+F)
        # Это полезно для сайтов без поля поиска (например, Додо Пицца)
        try:
            result = await self.find_text_on_page(text)

            if result["status"] == "success" and result.get("found"):
                return {
                    "status": "success",
                    "message": f"Поле поиска не найдено, но текст '{text}' найден на странице через браузерный поиск ({result['count']} совпадений)",
                    "method": "page_search",
                    "found": True,
                    "count": result["count"]
                }
            else:
                return {
                    "status": "warning",
                    "message": f"Поле поиска не найдено. Текст '{text}' не найден на странице через браузерный поиск. Возможно, нужно прокрутить страницу или загрузить больше элементов.",
                    "method": "page_search",
                    "found": False,
                    "tried_selectors": tried_selectors[:5]
                }
        except Exception as search_error:
            return {
                "status": "error",
                "message": f"Не удалось найти поле поиска. Попробовано {len(tried_selectors)} селекторов. Браузерный поиск также не сработал: {str(search_error)}",
                "tried_selectors": tried_selectors[:5],
                "errors": errors[:3]
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

            # Попытка 1: Ждём элемент и прокручиваем к нему
            try:
                # Ждём появления элемента
                await locator.wait_for(state="visible", timeout=10000)
                # Прокручиваем к элементу
                await locator.scroll_into_view_if_needed()
                await asyncio.sleep(0.5)
                # Кликаем
                await locator.click(timeout=5000)
                # Дополнительное ожидание для загрузки нового контента после клика
                await asyncio.sleep(1.5)
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

                    # Снова ждём и прокручиваем
                    await locator.wait_for(state="visible", timeout=5000)
                    await locator.scroll_into_view_if_needed()
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
                        await locator.scroll_into_view_if_needed()
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
            error_msg = str(e)

            # Более информативные сообщения об ошибках
            if "Timeout" in error_msg or "timeout" in error_msg:
                return {
                    "status": "error",
                    "message": (
                        f"Элемент с текстом '{text}' не найден на странице или не загрузился.\n"
                        f"Возможные причины:\n"
                        f"- Элемент всё ещё загружается (попробуйте scroll_down или подождите)\n"
                        f"- Текст не точно совпадает (попробуйте более короткий вариант)\n"
                        f"- Элемент находится в другом месте страницы"
                    )
                }
            else:
                return {
                    "status": "error",
                    "message": f"Ошибка клика по '{text}': {error_msg}"
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
            # Увеличенное ожидание для подгрузки lazy-loaded контента
            await asyncio.sleep(1.0)

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

    async def check_for_captcha(self) -> Dict[str, Any]:
        """
        Проверить наличие капчи на текущей странице

        Returns:
            Dict с информацией о капче
        """
        try:
            if not self.captcha_handler:
                return {
                    "status": "error",
                    "message": "Обработчик капч не инициализирован"
                }

            detection = await self.captcha_handler.detect_captcha()

            if detection["detected"]:
                return {
                    "status": "success",
                    "captcha_detected": True,
                    "captcha_type": detection["type"],
                    "message": detection["message"]
                }
            else:
                return {
                    "status": "success",
                    "captcha_detected": False,
                    "message": "Капча не обнаружена"
                }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Ошибка проверки капчи: {str(e)}"
            }

    async def solve_captcha_manually(self, timeout: int = 300) -> Dict[str, Any]:
        """
        Ожидать ручного решения капчи пользователем

        Args:
            timeout: Время ожидания в секундах (по умолчанию 5 минут)

        Returns:
            Dict с результатом решения капчи
        """
        try:
            if not self.captcha_handler:
                return {
                    "status": "error",
                    "message": "Обработчик капч не инициализирован"
                }

            # Сначала проверяем наличие капчи
            detection = await self.captcha_handler.detect_captcha()

            if not detection["detected"]:
                return {
                    "status": "success",
                    "message": "Капча не обнаружена, продолжаем работу",
                    "captcha_solved": True
                }

            # Если капча есть, ждём её решения
            print(f"\n⚠️  Обнаружена капча: {detection['message']}")
            print(f"⏳ Пожалуйста, решите капчу вручную в браузере")
            print(f"⏱️  Ожидание: {timeout} секунд\n")

            solve_result = await self.captcha_handler.wait_for_manual_solve(timeout)

            if solve_result["solved"]:
                return {
                    "status": "success",
                    "message": solve_result["message"],
                    "captcha_solved": True,
                    "duration": solve_result["duration"]
                }
            else:
                return {
                    "status": "error",
                    "message": solve_result["message"],
                    "captcha_solved": False,
                    "duration": solve_result["duration"]
                }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Ошибка при решении капчи: {str(e)}",
                "captcha_solved": False
            }

    # ═══════════════════════════════════════════════════════════════
    # МЕТОДЫ ДЛЯ РАБОТЫ С КОНСТРУКТОРОМ БЛЮД
    # ═══════════════════════════════════════════════════════════════

    async def get_dish_customization_options(self) -> Dict[str, Any]:
        """
        Получить доступные опции кастомизации блюда из модального окна.

        Парсит конструктор блюда и возвращает структурированную информацию
        о доступных размерах, ингредиентах для добавления/удаления,
        модификаторах и контроле количества.

        Returns:
            Dict с полями:
            - sizes: список доступных размеров
            - removable: ингредиенты которые можно убрать
            - addable: ингредиенты которые можно добавить
            - modifiers: дополнительные модификаторы (соусы и т.д.)
            - has_quantity_control: есть ли +/- контролы
            - current_price: текущая цена
        """
        try:
            await asyncio.sleep(0.5)  # Ждём загрузки модального окна

            result = {
                "status": "success",
                "sizes": [],
                "removable": [],
                "addable": [],
                "modifiers": [],
                "has_quantity_control": False,
                "current_price": None
            }

            # === ПАРСИНГ РАЗМЕРОВ ===
            size_selectors = [
                '[class*="size"] label',
                '[class*="Size"] label',
                '[data-testid*="size"]',
                'input[type="radio"][name*="size"] + label',
                '[class*="pizza-size"]',
                '[class*="product-size"]',
                '[class*="portion"]',
                'button[class*="size"]',
                '[role="radiogroup"] [role="radio"]'
            ]

            for selector in size_selectors:
                try:
                    elements = await self.page.locator(selector).all()
                    for elem in elements:
                        if await elem.is_visible():
                            text = await elem.inner_text()
                            text = text.strip()
                            if text and len(text) < 50:  # Фильтруем мусор
                                # Проверяем что это похоже на размер
                                size_keywords = ['см', 'см.', 'г', 'г.', 'мл', 'л',
                                               'маленьк', 'средн', 'больш', 'стандарт',
                                               'S', 'M', 'L', 'XL', 'XXL',
                                               'small', 'medium', 'large', 'мини', 'макси']
                                if any(kw.lower() in text.lower() for kw in size_keywords) or text[0].isdigit():
                                    if text not in result["sizes"]:
                                        result["sizes"].append(text)
                except:
                    continue

            # === ПАРСИНГ ИНГРЕДИЕНТОВ (УБРАТЬ) ===
            removable_selectors = [
                '[class*="ingredient"] input[type="checkbox"]',
                '[class*="remove"] label',
                '[class*="exclude"] label',
                '[class*="without"] label',
                '[class*="topping"] [class*="remove"]',
                '[class*="modifier"] input[type="checkbox"]:checked',
                'label:has(input[type="checkbox"]:checked)',
                '[class*="option"] input[type="checkbox"]'
            ]

            # Сначала попробуем найти уже выбранные чекбоксы (ингредиенты которые можно убрать)
            try:
                checked_checkboxes = await self.page.locator('input[type="checkbox"]:checked').all()
                for checkbox in checked_checkboxes:
                    try:
                        # Ищем текст в родительском элементе или соседнем label
                        parent = checkbox.locator('..')
                        text = await parent.inner_text()
                        text = text.strip()
                        if text and len(text) < 50 and text not in result["removable"]:
                            result["removable"].append(text)
                    except:
                        continue
            except:
                pass

            for selector in removable_selectors:
                try:
                    elements = await self.page.locator(selector).all()
                    for elem in elements:
                        if await elem.is_visible():
                            text = await elem.inner_text()
                            text = text.strip()
                            if text and len(text) < 50 and text not in result["removable"]:
                                result["removable"].append(text)
                except:
                    continue

            # === ПАРСИНГ ИНГРЕДИЕНТОВ (ДОБАВИТЬ) ===
            addable_selectors = [
                '[class*="addon"] label',
                '[class*="add-on"] label',
                '[class*="extra"] label',
                '[class*="topping"]:not([class*="remove"]) label',
                '[class*="additional"] label',
                'input[type="checkbox"]:not(:checked) + label',
                '[class*="option"]:not(:checked)',
                '[class*="supplement"]'
            ]

            for selector in addable_selectors:
                try:
                    elements = await self.page.locator(selector).all()
                    for elem in elements:
                        if await elem.is_visible():
                            text = await elem.inner_text()
                            text = text.strip()
                            if text and len(text) < 50:
                                # Исключаем уже добавленные в removable
                                if text not in result["addable"] and text not in result["removable"]:
                                    result["addable"].append(text)
                except:
                    continue

            # === ПАРСИНГ МОДИФИКАТОРОВ ===
            modifier_selectors = [
                '[class*="sauce"] label',
                '[class*="dressing"] label',
                '[class*="modifier"] label',
                'select option',
                '[class*="dropdown"] [class*="option"]'
            ]

            for selector in modifier_selectors:
                try:
                    elements = await self.page.locator(selector).all()
                    for elem in elements:
                        if await elem.is_visible():
                            text = await elem.inner_text()
                            text = text.strip()
                            if text and len(text) < 50:
                                if text not in result["modifiers"]:
                                    result["modifiers"].append(text)
                except:
                    continue

            # === ПРОВЕРКА КОНТРОЛЯ КОЛИЧЕСТВА ===
            quantity_selectors = [
                '[class*="counter"]',
                '[class*="quantity"]',
                '[class*="stepper"]',
                'button:has-text("+")',
                'button:has-text("-")',
                '[class*="amount"]'
            ]

            for selector in quantity_selectors:
                try:
                    elements = await self.page.locator(selector).all()
                    if len(elements) > 0:
                        for elem in elements:
                            if await elem.is_visible():
                                result["has_quantity_control"] = True
                                break
                except:
                    continue
                if result["has_quantity_control"]:
                    break

            # === ПАРСИНГ ТЕКУЩЕЙ ЦЕНЫ ===
            price_selectors = [
                '[class*="price"]',
                '[class*="Price"]',
                '[class*="cost"]',
                '[class*="total"]',
                '[class*="sum"]'
            ]

            for selector in price_selectors:
                try:
                    elements = await self.page.locator(selector).all()
                    for elem in elements:
                        if await elem.is_visible():
                            text = await elem.inner_text()
                            # Ищем число с символом рубля или просто число
                            import re
                            price_match = re.search(r'(\d[\d\s]*[₽руб\.]*|\d+)', text)
                            if price_match:
                                result["current_price"] = text.strip()
                                break
                except:
                    continue
                if result["current_price"]:
                    break

            # Формируем сообщение для агента
            summary_parts = []
            if result["sizes"]:
                summary_parts.append(f"Размеры: {', '.join(result['sizes'])}")
            if result["removable"]:
                summary_parts.append(f"Можно убрать: {', '.join(result['removable'])}")
            if result["addable"]:
                summary_parts.append(f"Можно добавить: {', '.join(result['addable'])}")
            if result["modifiers"]:
                summary_parts.append(f"Модификаторы: {', '.join(result['modifiers'])}")
            if result["current_price"]:
                summary_parts.append(f"Цена: {result['current_price']}")

            result["summary"] = " | ".join(summary_parts) if summary_parts else "Опции кастомизации не найдены"

            return result

        except Exception as e:
            return {
                "status": "error",
                "message": f"Ошибка парсинга опций кастомизации: {str(e)}"
            }

    async def toggle_option(self, option_text: str, action: str = "select") -> Dict[str, Any]:
        """
        Переключить опцию в конструкторе блюда.

        Args:
            option_text: текст опции для поиска (например "Лук", "Сыр")
            action: действие - "add" (добавить), "remove" (убрать), "select" (выбрать)

        Returns:
            Dict с результатом операции
        """
        try:
            await asyncio.sleep(0.3)

            # Стратегия 1: Ищем элемент напрямую по тексту и кликаем
            try:
                locator = self.page.get_by_text(option_text, exact=False).first
                if await locator.is_visible():
                    await locator.click(timeout=3000)
                    await asyncio.sleep(0.5)
                    return {
                        "status": "success",
                        "message": f"{'Убрали' if action == 'remove' else 'Добавили' if action == 'add' else 'Выбрали'} '{option_text}'",
                        "action": action
                    }
            except:
                pass

            # Стратегия 2: Ищем чекбокс/радиокнопку рядом с текстом
            checkbox_selectors = [
                f'label:has-text("{option_text}") input',
                f'label:has-text("{option_text}")',
                f'[class*="option"]:has-text("{option_text}")',
                f'[class*="ingredient"]:has-text("{option_text}")',
                f'[class*="topping"]:has-text("{option_text}")',
                f'[class*="modifier"]:has-text("{option_text}")'
            ]

            for selector in checkbox_selectors:
                try:
                    element = self.page.locator(selector).first
                    if await element.is_visible():
                        await element.click(timeout=3000)
                        await asyncio.sleep(0.5)
                        return {
                            "status": "success",
                            "message": f"{'Убрали' if action == 'remove' else 'Добавили' if action == 'add' else 'Выбрали'} '{option_text}'",
                            "action": action
                        }
                except:
                    continue

            # Стратегия 3: Для действия remove ищем кнопку удаления рядом с текстом
            if action == "remove":
                try:
                    # Находим элемент с текстом
                    text_elem = self.page.get_by_text(option_text, exact=False).first
                    if await text_elem.is_visible():
                        # Ищем кнопку удаления в родительском элементе
                        parent = text_elem.locator('..')
                        remove_btn = parent.locator('[class*="remove"], [class*="delete"], button:has-text("×"), button:has-text("-")').first
                        if await remove_btn.is_visible():
                            await remove_btn.click(timeout=3000)
                            await asyncio.sleep(0.5)
                            return {
                                "status": "success",
                                "message": f"Убрали '{option_text}' (кнопка удаления)",
                                "action": action
                            }
                except:
                    pass

            # Стратегия 4: Для действия add ищем кнопку добавления
            if action == "add":
                try:
                    text_elem = self.page.get_by_text(option_text, exact=False).first
                    if await text_elem.is_visible():
                        parent = text_elem.locator('..')
                        add_btn = parent.locator('[class*="add"], button:has-text("+")').first
                        if await add_btn.is_visible():
                            await add_btn.click(timeout=3000)
                            await asyncio.sleep(0.5)
                            return {
                                "status": "success",
                                "message": f"Добавили '{option_text}' (кнопка добавления)",
                                "action": action
                            }
                except:
                    pass

            return {
                "status": "error",
                "message": f"Не удалось найти опцию '{option_text}' для действия '{action}'"
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Ошибка переключения опции: {str(e)}"
            }

    async def adjust_quantity(self, item_text: str, action: str) -> Dict[str, Any]:
        """
        Изменить количество ингредиента (+ или -).

        Args:
            item_text: текст ингредиента (например "Сыр", "Бекон")
            action: "increase" (увеличить) или "decrease" (уменьшить)

        Returns:
            Dict с результатом операции
        """
        try:
            await asyncio.sleep(0.3)

            button_text = "+" if action == "increase" else "-"
            action_word = "Увеличили" if action == "increase" else "Уменьшили"

            # Стратегия 1: Находим элемент с текстом, затем ищем кнопку +/- рядом
            try:
                text_elem = self.page.get_by_text(item_text, exact=False).first
                if await text_elem.is_visible():
                    # Ищем в родительском элементе
                    parent = text_elem.locator('..')

                    # Пробуем найти кнопку в нескольких уровнях вверх
                    for _ in range(3):
                        button_selectors = [
                            f'button:has-text("{button_text}")',
                            f'[class*="btn"]:has-text("{button_text}")',
                            f'[class*="counter"] button:has-text("{button_text}")',
                            f'[class*="quantity"] button:has-text("{button_text}")',
                            f'[class*="stepper"] button:has-text("{button_text}")'
                        ]

                        for selector in button_selectors:
                            try:
                                btn = parent.locator(selector).first
                                if await btn.is_visible():
                                    await btn.click(timeout=3000)
                                    await asyncio.sleep(0.5)
                                    return {
                                        "status": "success",
                                        "message": f"{action_word} количество '{item_text}'",
                                        "action": action
                                    }
                            except:
                                continue

                        # Поднимаемся на уровень выше
                        parent = parent.locator('..')
            except:
                pass

            # Стратегия 2: Глобальный поиск кнопок +/-
            try:
                # Ищем все контролы количества на странице
                quantity_controls = await self.page.locator('[class*="counter"], [class*="quantity"], [class*="stepper"]').all()

                for control in quantity_controls:
                    try:
                        control_text = await control.inner_text()
                        if item_text.lower() in control_text.lower():
                            btn = control.locator(f'button:has-text("{button_text}")').first
                            if await btn.is_visible():
                                await btn.click(timeout=3000)
                                await asyncio.sleep(0.5)
                                return {
                                    "status": "success",
                                    "message": f"{action_word} количество '{item_text}'",
                                    "action": action
                                }
                    except:
                        continue
            except:
                pass

            return {
                "status": "error",
                "message": f"Не удалось найти контроль количества для '{item_text}'"
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Ошибка изменения количества: {str(e)}"
            }

    async def select_size(self, size_text: str) -> Dict[str, Any]:
        """
        Выбрать размер блюда.

        Args:
            size_text: текст размера (например "Большая", "30 см", "L")

        Returns:
            Dict с результатом операции
        """
        try:
            await asyncio.sleep(0.3)

            # Стратегия 1: Прямой клик по тексту размера
            try:
                locator = self.page.get_by_text(size_text, exact=False).first
                if await locator.is_visible():
                    await locator.click(timeout=3000)
                    await asyncio.sleep(0.5)
                    return {
                        "status": "success",
                        "message": f"Выбран размер '{size_text}'"
                    }
            except:
                pass

            # Стратегия 2: Ищем в элементах размера
            size_selectors = [
                f'[class*="size"]:has-text("{size_text}")',
                f'[class*="Size"]:has-text("{size_text}")',
                f'label:has-text("{size_text}")',
                f'button:has-text("{size_text}")',
                f'[role="radio"]:has-text("{size_text}")',
                f'[class*="option"]:has-text("{size_text}")',
                f'[class*="portion"]:has-text("{size_text}")'
            ]

            for selector in size_selectors:
                try:
                    element = self.page.locator(selector).first
                    if await element.is_visible():
                        await element.click(timeout=3000)
                        await asyncio.sleep(0.5)
                        return {
                            "status": "success",
                            "message": f"Выбран размер '{size_text}'"
                        }
                except:
                    continue

            # Стратегия 3: Ищем радиокнопку с label
            try:
                label = self.page.locator(f'label:has-text("{size_text}")').first
                if await label.is_visible():
                    # Пробуем кликнуть по label
                    await label.click(timeout=3000)
                    await asyncio.sleep(0.5)
                    return {
                        "status": "success",
                        "message": f"Выбран размер '{size_text}'"
                    }
            except:
                pass

            return {
                "status": "error",
                "message": f"Не удалось выбрать размер '{size_text}'"
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Ошибка выбора размера: {str(e)}"
            }

    async def scroll_to_text(self, text: str, highlight: bool = True, highlight_all: bool = False) -> Dict[str, Any]:
        """
        Найти текст на странице, прокрутить к нему и подсветить

        Args:
            text: Текст для поиска
            highlight: Подсветить элемент (по умолчанию True)
            highlight_all: Подсветить ВСЕ найденные элементы (по умолчанию False)

        Returns:
            Результат операции
        """
        try:
            # Ищем элементы с текстом
            if highlight_all:
                # Ищем все элементы
                elements = self.page.locator(f'text="{text}"')
                count = await elements.count()

                if count == 0:
                    # Пробуем частичное совпадение
                    elements = self.page.locator(f'text={text}')
                    count = await elements.count()

                if count == 0:
                    return {
                        "status": "error",
                        "message": f"Текст '{text}' не найден на странице"
                    }

                # Прокручиваем к первому элементу
                await elements.first.scroll_into_view_if_needed()
                await asyncio.sleep(0.5)

                # Подсвечиваем ВСЕ найденные элементы
                if highlight:
                    await self.page.evaluate("""
                        (text) => {
                            // Убираем предыдущую подсветку
                            document.querySelectorAll('.ai-highlight').forEach(el => {
                                el.classList.remove('ai-highlight');
                            });

                            // Ищем ВСЕ элементы с текстом
                            const xpath = `//text()[contains(., '${text}')]/parent::*`;
                            const result = document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);

                            let highlightedCount = 0;
                            for (let i = 0; i < result.snapshotLength; i++) {
                                const element = result.snapshotItem(i);
                                if (element) {
                                    element.classList.add('ai-highlight');
                                    highlightedCount++;
                                }
                            }

                            // Добавляем стили если их ещё нет
                            if (!document.getElementById('ai-highlight-styles')) {
                                const style = document.createElement('style');
                                style.id = 'ai-highlight-styles';
                                style.textContent = `
                                    .ai-highlight {
                                        outline: 3px solid #4CAF50 !important;
                                        outline-offset: 2px !important;
                                        background-color: rgba(76, 175, 80, 0.1) !important;
                                        transition: all 0.3s ease !important;
                                    }
                                `;
                                document.head.appendChild(style);
                            }

                            return highlightedCount;
                        }
                    """, text)

                return {
                    "status": "success",
                    "message": f"Найдено {count} элементов с текстом '{text}', все подсвечены",
                    "count": count
                }
            else:
                # Ищем только первый элемент
                element = self.page.locator(f'text="{text}"').first

                # Проверяем что элемент найден
                if await element.count() == 0:
                    # Пробуем частичное совпадение
                    element = self.page.locator(f'text={text}').first

                    if await element.count() == 0:
                        return {
                            "status": "error",
                            "message": f"Текст '{text}' не найден на странице"
                        }

                # Прокручиваем к элементу
                await element.scroll_into_view_if_needed()
                await asyncio.sleep(0.5)  # Плавная прокрутка

                # Подсвечиваем элемент
                if highlight:
                    await self.page.evaluate("""
                        (text) => {
                            // Убираем предыдущую подсветку
                            document.querySelectorAll('.ai-highlight').forEach(el => {
                                el.classList.remove('ai-highlight');
                            });

                            // Ищем элемент с текстом
                            const xpath = `//text()[contains(., '${text}')]/parent::*`;
                            const result = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
                            const element = result.singleNodeValue;

                            if (element) {
                                // Добавляем подсветку
                                element.classList.add('ai-highlight');

                                // Добавляем стили если их ещё нет
                                if (!document.getElementById('ai-highlight-styles')) {
                                    const style = document.createElement('style');
                                    style.id = 'ai-highlight-styles';
                                    style.textContent = `
                                        .ai-highlight {
                                            outline: 3px solid #4CAF50 !important;
                                            outline-offset: 2px !important;
                                            background-color: rgba(76, 175, 80, 0.1) !important;
                                            transition: all 0.3s ease !important;
                                        }
                                    `;
                                    document.head.appendChild(style);
                                }
                            }
                        }
                    """, text)

                return {
                    "status": "success",
                    "message": f"Прокрутили к тексту '{text}' и подсветили"
                }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Ошибка при поиске текста: {str(e)}"
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