"""
Captcha Handler - обработка и решение капч

Поддерживаемые типы капч:
- reCAPTCHA v2/v3
- hCaptcha
- CloudFlare Turnstile
- Yandex SmartCaptcha

Методы решения:
1. Детектирование капчи на странице
2. Пауза для ручного решения
3. Интеграция с сервисами (2Captcha, AntiCaptcha)
4. AI-решение через Claude Vision (опционально)
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from playwright.async_api import Page
import time


class CaptchaType:
    """Типы капч"""
    RECAPTCHA_V2 = "recaptcha_v2"
    RECAPTCHA_V3 = "recaptcha_v3"
    HCAPTCHA = "hcaptcha"
    CLOUDFLARE = "cloudflare"
    YANDEX = "yandex"
    UNKNOWN = "unknown"


class CaptchaHandler:
    """Обработчик капч для AI Browser Agent"""

    def __init__(self, page: Page, solver_service: Optional[str] = None, api_key: Optional[str] = None):
        """
        Args:
            page: Playwright Page объект
            solver_service: Сервис для автоматического решения ("2captcha", "anticaptcha", None)
            api_key: API ключ для сервиса (если используется)
        """
        self.page = page
        self.solver_service = solver_service
        self.api_key = api_key
        self.logger = logging.getLogger(__name__)

    async def detect_captcha(self) -> Dict[str, Any]:
        """
        Детектировать наличие капчи на странице

        Returns:
            Dict с информацией о капче:
            - detected: bool - обнаружена ли капча
            - type: str - тип капчи
            - selectors: list - найденные селекторы капчи
            - message: str - сообщение для пользователя
        """
        try:
            captcha_info = {
                "detected": False,
                "type": CaptchaType.UNKNOWN,
                "selectors": [],
                "message": ""
            }

            # Проверка reCAPTCHA v2
            recaptcha_v2 = await self._check_recaptcha_v2()
            if recaptcha_v2["found"]:
                captcha_info["detected"] = True
                captcha_info["type"] = CaptchaType.RECAPTCHA_V2
                captcha_info["selectors"] = recaptcha_v2["selectors"]
                captcha_info["message"] = "Обнаружена Google reCAPTCHA v2"
                return captcha_info

            # Проверка reCAPTCHA v3 (скрытая)
            recaptcha_v3 = await self._check_recaptcha_v3()
            if recaptcha_v3["found"]:
                captcha_info["detected"] = True
                captcha_info["type"] = CaptchaType.RECAPTCHA_V3
                captcha_info["message"] = "Обнаружена Google reCAPTCHA v3 (автоматическая)"
                return captcha_info

            # Проверка hCaptcha
            hcaptcha = await self._check_hcaptcha()
            if hcaptcha["found"]:
                captcha_info["detected"] = True
                captcha_info["type"] = CaptchaType.HCAPTCHA
                captcha_info["selectors"] = hcaptcha["selectors"]
                captcha_info["message"] = "Обнаружена hCaptcha"
                return captcha_info

            # Проверка CloudFlare Turnstile
            cloudflare = await self._check_cloudflare()
            if cloudflare["found"]:
                captcha_info["detected"] = True
                captcha_info["type"] = CaptchaType.CLOUDFLARE
                captcha_info["selectors"] = cloudflare["selectors"]
                captcha_info["message"] = "Обнаружена CloudFlare Turnstile"
                return captcha_info

            # Проверка Yandex SmartCaptcha
            yandex = await self._check_yandex_captcha()
            if yandex["found"]:
                captcha_info["detected"] = True
                captcha_info["type"] = CaptchaType.YANDEX
                captcha_info["selectors"] = yandex["selectors"]
                captcha_info["message"] = "Обнаружена Yandex SmartCaptcha"
                return captcha_info

            # Проверка по ключевым словам на странице
            text_indicators = await self._check_text_indicators()
            if text_indicators["found"]:
                captcha_info["detected"] = True
                captcha_info["type"] = CaptchaType.UNKNOWN
                captcha_info["message"] = f"Возможна капча (найдено: {text_indicators['keywords']})"
                return captcha_info

            return captcha_info

        except Exception as e:
            self.logger.error(f"Ошибка при детектировании капчи: {e}")
            return {
                "detected": False,
                "type": CaptchaType.UNKNOWN,
                "selectors": [],
                "message": "",
                "error": str(e)
            }

    async def _check_recaptcha_v2(self) -> Dict[str, Any]:
        """Проверка наличия reCAPTCHA v2"""
        selectors = [
            'iframe[src*="recaptcha"]',
            'iframe[title*="reCAPTCHA"]',
            '.g-recaptcha',
            '[class*="g-recaptcha"]',
            '#recaptcha'
        ]

        found_selectors = []
        for selector in selectors:
            try:
                elements = await self.page.locator(selector).all()
                if len(elements) > 0:
                    found_selectors.append(selector)
            except:
                continue

        return {
            "found": len(found_selectors) > 0,
            "selectors": found_selectors
        }

    async def _check_recaptcha_v3(self) -> Dict[str, Any]:
        """Проверка наличия reCAPTCHA v3 (скрытая версия)"""
        try:
            # reCAPTCHA v3 работает в фоне, проверяем наличие скриптов
            has_script = await self.page.evaluate("""
                () => {
                    const scripts = Array.from(document.querySelectorAll('script'));
                    return scripts.some(script =>
                        script.src.includes('recaptcha') ||
                        script.textContent.includes('grecaptcha')
                    );
                }
            """)

            return {"found": has_script}
        except:
            return {"found": False}

    async def _check_hcaptcha(self) -> Dict[str, Any]:
        """Проверка наличия hCaptcha"""
        selectors = [
            'iframe[src*="hcaptcha"]',
            '.h-captcha',
            '[class*="h-captcha"]',
            '#hcaptcha'
        ]

        found_selectors = []
        for selector in selectors:
            try:
                elements = await self.page.locator(selector).all()
                if len(elements) > 0:
                    found_selectors.append(selector)
            except:
                continue

        return {
            "found": len(found_selectors) > 0,
            "selectors": found_selectors
        }

    async def _check_cloudflare(self) -> Dict[str, Any]:
        """Проверка CloudFlare Turnstile/Challenge"""
        selectors = [
            'iframe[src*="challenges.cloudflare"]',
            '#cf-challenge-running',
            '.cf-browser-verification',
            '[id*="cloudflare"]'
        ]

        found_selectors = []
        for selector in selectors:
            try:
                elements = await self.page.locator(selector).all()
                if len(elements) > 0:
                    found_selectors.append(selector)
            except:
                continue

        # Проверка текста CloudFlare
        try:
            page_content = await self.page.content()
            if "cloudflare" in page_content.lower() and "checking" in page_content.lower():
                found_selectors.append("text:cloudflare")
        except:
            pass

        return {
            "found": len(found_selectors) > 0,
            "selectors": found_selectors
        }

    async def _check_yandex_captcha(self) -> Dict[str, Any]:
        """Проверка Yandex SmartCaptcha"""
        selectors = [
            'iframe[src*="captcha"]',
            'iframe[src*="smartcaptcha"]',
            '[class*="SmartCaptcha"]',
            '#captcha'
        ]

        found_selectors = []
        for selector in selectors:
            try:
                elements = await self.page.locator(selector).all()
                if len(elements) > 0:
                    # Проверяем, что это именно Yandex
                    for elem in elements:
                        src = await elem.get_attribute("src") if await elem.get_attribute("src") else ""
                        if "yandex" in src.lower() or "captcha" in src.lower():
                            found_selectors.append(selector)
                            break
            except:
                continue

        return {
            "found": len(found_selectors) > 0,
            "selectors": found_selectors
        }

    async def _check_text_indicators(self) -> Dict[str, Any]:
        """Проверка текстовых индикаторов капчи"""
        keywords = [
            "captcha",
            "проверка безопасности",
            "security check",
            "verify you are human",
            "подтвердите, что вы не робот",
            "I'm not a robot",
            "я не робот"
        ]

        found_keywords = []
        try:
            page_text = await self.page.inner_text("body")
            page_text_lower = page_text.lower()

            for keyword in keywords:
                if keyword.lower() in page_text_lower:
                    found_keywords.append(keyword)
        except:
            pass

        return {
            "found": len(found_keywords) > 0,
            "keywords": found_keywords
        }

    async def wait_for_manual_solve(self, timeout: int = 300) -> Dict[str, Any]:
        """
        Ожидание ручного решения капчи пользователем

        Args:
            timeout: Максимальное время ожидания в секундах (по умолчанию 5 минут)

        Returns:
            Dict с результатом:
            - solved: bool - решена ли капча
            - method: str - метод решения
            - duration: float - время решения
            - message: str
        """
        self.logger.info(f"Ожидание ручного решения капчи (таймаут: {timeout}с)...")

        start_time = time.time()
        check_interval = 2  # Проверять каждые 2 секунды

        try:
            while time.time() - start_time < timeout:
                # Проверяем, исчезла ли капча
                detection = await self.detect_captcha()

                if not detection["detected"]:
                    duration = time.time() - start_time
                    self.logger.info(f"Капча решена вручную за {duration:.1f}с")
                    return {
                        "solved": True,
                        "method": "manual",
                        "duration": duration,
                        "message": f"Капча решена вручную за {duration:.1f}с"
                    }

                await asyncio.sleep(check_interval)

            # Таймаут истёк
            duration = time.time() - start_time
            return {
                "solved": False,
                "method": "manual",
                "duration": duration,
                "message": f"Таймаут ожидания ({timeout}с). Капча не решена."
            }

        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"Ошибка при ожидании решения капчи: {e}")
            return {
                "solved": False,
                "method": "manual",
                "duration": duration,
                "message": f"Ошибка: {str(e)}"
            }

    async def handle_captcha_if_present(self, auto_wait: bool = True, timeout: int = 300) -> Dict[str, Any]:
        """
        Обнаружить и обработать капчу, если она присутствует

        Args:
            auto_wait: Автоматически ждать ручного решения
            timeout: Таймаут ожидания в секундах

        Returns:
            Dict с результатом обработки:
            - captcha_detected: bool
            - captcha_type: str
            - handled: bool - обработана ли капча
            - method: str - метод обработки
            - message: str
        """
        # Детектируем капчу
        detection = await self.detect_captcha()

        if not detection["detected"]:
            return {
                "captcha_detected": False,
                "captcha_type": None,
                "handled": True,
                "method": None,
                "message": "Капча не обнаружена"
            }

        self.logger.warning(f"Обнаружена капча: {detection['message']}")

        # Если настроена автоматическая обработка через сервис
        if self.solver_service and self.api_key:
            self.logger.info(f"Попытка автоматического решения через {self.solver_service}...")
            # TODO: Интеграция с 2Captcha/AntiCaptcha
            # solver_result = await self._solve_with_service(detection)
            # if solver_result["success"]:
            #     return solver_result
            pass

        # Ручное решение
        if auto_wait:
            print(f"\n⚠️  {detection['message']}")
            print(f"⏳ Пожалуйста, решите капчу вручную в браузере.")
            print(f"⏱️  Ожидание до {timeout} секунд...\n")

            solve_result = await self.wait_for_manual_solve(timeout)

            return {
                "captcha_detected": True,
                "captcha_type": detection["type"],
                "handled": solve_result["solved"],
                "method": "manual",
                "duration": solve_result["duration"],
                "message": solve_result["message"]
            }
        else:
            return {
                "captcha_detected": True,
                "captcha_type": detection["type"],
                "handled": False,
                "method": None,
                "message": f"Капча обнаружена: {detection['message']}. Требуется ручное вмешательство."
            }

    async def is_captcha_visible(self) -> bool:
        """
        Быстрая проверка: видна ли капча на странице

        Returns:
            bool - True если капча видна
        """
        detection = await self.detect_captcha()
        return detection["detected"]


# Утилитарные функции для интеграции в action_executor

async def check_page_for_captcha(page: Page) -> Dict[str, Any]:
    """
    Быстрая проверка страницы на наличие капчи

    Args:
        page: Playwright Page объект

    Returns:
        Dict с результатом детектирования
    """
    handler = CaptchaHandler(page)
    return await handler.detect_captcha()


async def handle_captcha_auto(page: Page, timeout: int = 300) -> Dict[str, Any]:
    """
    Автоматически обработать капчу, если она есть

    Args:
        page: Playwright Page объект
        timeout: Максимальное время ожидания ручного решения

    Returns:
        Dict с результатом обработки
    """
    handler = CaptchaHandler(page)
    return await handler.handle_captcha_if_present(auto_wait=True, timeout=timeout)
