"""
ActionExecutor - исполнитель команд от AI агента
Преобразует JSON команды в вызовы BrowserTools
"""
from typing import Dict, Any, Callable
from src.tools.browser_tools import BrowserTools

class ActionExecutor:
    """Исполнитель действий браузера"""

    def __init__(self, browser_tools: BrowserTools):
        self.tools = browser_tools

        # Маппинг команд на методы BrowserTools
        self.action_map: Dict[str, Callable] = {
            "navigate": self._execute_navigate,
            "click_by_text": self._execute_click_by_text,
            "get_page_text": self._execute_get_page_text,
            "scroll_down": self._execute_scroll_down,
            "scroll_up": self._execute_scroll_up,
            "press_key": self._execute_press_key,
            "type_text": self._execute_type_text,
            "take_screenshot": self._execute_take_screenshot,
            "wait_for_text": self._execute_wait_for_text,
            "find_text": self._execute_find_text,
            "close_modal": self._execute_close_modal,
            "wait_for_modal": self._execute_wait_for_modal,
            "get_modal_text": self._execute_get_modal_text,
        }

    async def execute(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Выполнить действие из JSON команды

        Args:
            action: Словарь с полями:
                - action: название действия
                - params: параметры действия
                - reasoning: объяснение (опционально)

        Returns:
            Результат выполнения действия
        """
        action_name = action.get("action")
        params = action.get("params", {})
        reasoning = action.get("reasoning", "")

        if not action_name:
            return {
                "status": "error",
                "message": "Не указано название действия"
            }

        if action_name not in self.action_map:
            return {
                "status": "error",
                "message": f"Неизвестное действие: {action_name}"
            }

        # Выполняем действие
        try:
            print(f"\n🔧 Выполняю: {action_name}")
            if reasoning:
                print(f"   Причина: {reasoning}")
            print(f"   Параметры: {params}")

            result = await self.action_map[action_name](**params)

            print(f"   ✓ Результат: {result.get('status', 'unknown')}")

            return result

        except Exception as e:
            error_msg = f"Ошибка выполнения {action_name}: {str(e)}"
            print(f"   ❌ {error_msg}")
            return {
                "status": "error",
                "message": error_msg
            }

    # Методы-обёртки для каждого действия

    async def _execute_navigate(self, url: str) -> Dict[str, Any]:
        """Открыть URL"""
        return await self.tools.navigate(url)

    async def _execute_click_by_text(self, text: str, exact: bool = False) -> Dict[str, Any]:
        """Кликнуть по тексту"""
        return await self.tools.click_by_text(text, exact=exact)

    async def _execute_get_page_text(self) -> Dict[str, Any]:
        """Получить текст страницы"""
        return await self.tools.get_page_text()

    async def _execute_scroll_down(self, pixels: int = 500) -> Dict[str, Any]:
        """Прокрутить вниз"""
        return await self.tools.scroll_down(pixels=pixels)

    async def _execute_scroll_up(self, pixels: int = 500) -> Dict[str, Any]:
        """Прокрутить вверх"""
        return await self.tools.scroll_up(pixels=pixels)

    async def _execute_press_key(self, key: str) -> Dict[str, Any]:
        """Нажать клавишу"""
        return await self.tools.press_key(key)

    async def _execute_type_text(self, selector: str, text: str) -> Dict[str, Any]:
        """Ввести текст в поле"""
        return await self.tools.type_text(selector, text)

    async def _execute_take_screenshot(self, filename: str = None) -> Dict[str, Any]:
        """Сделать скриншот"""
        return await self.tools.take_screenshot(filename)

    async def _execute_wait_for_text(self, text: str, timeout: int = 10000) -> Dict[str, Any]:
        """Дождаться появления текста"""
        return await self.tools.wait_for_text(text, timeout=timeout)

    async def _execute_find_text(self, search_text: str) -> Dict[str, Any]:
        """Найти текст на странице (Ctrl+F)"""
        return await self.tools.find_text_on_page(search_text)

    async def _execute_close_modal(self) -> Dict[str, Any]:
        """Закрыть модальное окно"""
        return await self.tools.close_modal()

    async def _execute_wait_for_modal(self, timeout: int = 5000) -> Dict[str, Any]:
        """Подождать появления модального окна"""
        return await self.tools.wait_for_modal(timeout=timeout)

    async def _execute_get_modal_text(self) -> Dict[str, Any]:
        """Получить текст из модального окна"""
        return await self.tools.get_modal_text()

    def get_available_actions(self) -> list:
        """Получить список доступных действий"""
        return list(self.action_map.keys())
