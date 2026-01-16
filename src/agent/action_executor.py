"""
ActionExecutor - исполнитель команд от AI агента
Преобразует JSON команды в вызовы BrowserTools
"""
import logging
from typing import Dict, Any, Callable, List
from src.tools.browser_tools import BrowserTools

class ActionExecutor:
    """Исполнитель действий браузера с graceful degradation"""

    def __init__(self, browser_tools: BrowserTools):
        self.tools = browser_tools
        self.logger = logging.getLogger(__name__)

        # История ошибок для аналитики
        self.error_history: List[Dict[str, Any]] = []

        # Маппинг команд на методы BrowserTools
        self.action_map: Dict[str, Callable] = {
            "navigate": self._execute_navigate,
            "click_by_text": self._execute_click_by_text,
            "get_page_text": self._execute_get_page_text,
            "scroll_down": self._execute_scroll_down,
            "scroll_up": self._execute_scroll_up,
            "press_key": self._execute_press_key,
            "type_text": self._execute_type_text,
            "search_and_type": self._execute_search_and_type,  # Умный поиск
            "take_screenshot": self._execute_take_screenshot,
            "wait_for_text": self._execute_wait_for_text,
            "wait": self._execute_wait,  # Пауза
            "find_text": self._execute_find_text,
            "close_modal": self._execute_close_modal,
            "wait_for_modal": self._execute_wait_for_modal,
            "get_modal_text": self._execute_get_modal_text,
            # Навигация к элементам
            "scroll_to_text": self._execute_scroll_to_text,
            # Конструктор блюд
            "get_dish_customization_options": self._execute_get_dish_customization_options,
            "toggle_option": self._execute_toggle_option,
            "adjust_quantity": self._execute_adjust_quantity,
            "select_size": self._execute_select_size,
            # Завершение задачи
            "done": self._execute_done,
            "respond": self._execute_done,  # алиас
            "stop": self._execute_done,     # алиас для совместимости
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
            self.logger.info(f"Выполнение действия: {action_name} с параметрами {params}")

            result = await self.action_map[action_name](**params)

            # Выводим результат для пользователя
            status = result.get('status', 'unknown')
            if status == 'success':
                print(f"✅ Действие выполнено успешно: {action_name}")

                # Дополнительная информация о результате
                if action_name == "navigate" and "url" in result:
                    print(f"   Открыта страница: {result['url']}")
                elif action_name == "get_page_text" and "text" in result:
                    text_preview = result["text"][:100].replace('\n', ' ')
                    if result.get("truncated"):
                        print(f"   Прочитан текст ({result.get('original_length')} символов, обрезано до {len(result['text'])}): {text_preview}...")
                    else:
                        print(f"   Прочитан текст ({len(result['text'])} символов): {text_preview}...")
                elif action_name == "click_by_text":
                    print(f"   Клик выполнен по тексту: {params.get('text', 'неизвестно')}")
                elif "message" in result:
                    print(f"   {result['message']}")
            elif status == 'done':
                # Действие done - это успешное завершение задачи, не ошибка
                print(f"✅ Задача завершена")
            else:
                error_msg = result.get('message', 'Неизвестная ошибка')
                print(f"❌ Ошибка при выполнении {action_name}: {error_msg}")

            return result

        except TypeError as e:
            # Ошибка параметров - graceful degradation
            error_msg = f"Неверные параметры для {action_name}: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self._log_error(action_name, "TypeError", str(e), params)

            print(f"   ❌ {error_msg}")
            return {
                "status": "error",
                "error_type": "parameter_error",
                "message": error_msg,
                "suggestion": "Проверьте формат параметров для этого действия"
            }

        except AttributeError as e:
            # Ошибка отсутствующего атрибута
            error_msg = f"Внутренняя ошибка в {action_name}: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self._log_error(action_name, "AttributeError", str(e), params)

            print(f"   ❌ {error_msg}")
            return {
                "status": "error",
                "error_type": "internal_error",
                "message": error_msg,
                "suggestion": "Попробуйте альтернативное действие"
            }

        except Exception as e:
            # Общая ошибка - максимум информации для отладки
            error_msg = f"Ошибка выполнения {action_name}: {str(e)}"
            error_type = type(e).__name__
            self.logger.error(f"{error_type}: {error_msg}", exc_info=True)
            self._log_error(action_name, error_type, str(e), params)

            print(f"   ❌ {error_msg}")
            return {
                "status": "error",
                "error_type": error_type,
                "message": error_msg
            }

    def _log_error(self, action_name: str, error_type: str, error_msg: str, params: Dict[str, Any]):
        """Логировать ошибку для дальнейшего анализа"""
        from datetime import datetime

        self.error_history.append({
            "timestamp": datetime.now().isoformat(),
            "action": action_name,
            "error_type": error_type,
            "error": error_msg,
            "params": params
        })

        # Ограничиваем размер истории
        if len(self.error_history) > 100:
            self.error_history = self.error_history[-100:]

    def get_error_summary(self) -> Dict[str, Any]:
        """Получить сводку по ошибкам для анализа"""
        if not self.error_history:
            return {"total_errors": 0}

        error_types = {}
        action_errors = {}

        for error in self.error_history:
            # Подсчёт по типам ошибок
            etype = error["error_type"]
            error_types[etype] = error_types.get(etype, 0) + 1

            # Подсчёт по действиям
            action = error["action"]
            action_errors[action] = action_errors.get(action, 0) + 1

        return {
            "total_errors": len(self.error_history),
            "by_type": error_types,
            "by_action": action_errors,
            "recent_errors": self.error_history[-5:]  # Последние 5
        }

    # Методы-обёртки для каждого действия

    async def _execute_navigate(self, url: str, **kwargs) -> Dict[str, Any]:
        """Открыть URL"""
        return await self.tools.navigate(url)

    async def _execute_click_by_text(self, text: str, exact: bool = False, **kwargs) -> Dict[str, Any]:
        """Кликнуть по тексту"""
        return await self.tools.click_by_text(text, exact=exact)

    async def _execute_get_page_text(self, max_length: int = 800, **kwargs) -> Dict[str, Any]:
        """Получить текст страницы с ограничением длины"""
        result = await self.tools.get_page_text()

        # Ограничиваем длину текста
        if result.get("status") == "success" and "text" in result:
            original_length = len(result["text"])
            if original_length > max_length:
                result["text"] = result["text"][:max_length]
                result["truncated"] = True
                result["original_length"] = original_length
                result["message"] = f"Текст обрезан до {max_length} символов (было {original_length})"

        return result

    async def _execute_scroll_down(self, pixels: int = 500, **kwargs) -> Dict[str, Any]:
        """Прокрутить вниз"""
        return await self.tools.scroll_down(pixels=pixels)

    async def _execute_scroll_up(self, pixels: int = 500, **kwargs) -> Dict[str, Any]:
        """Прокрутить вверх"""
        return await self.tools.scroll_up(pixels=pixels)

    async def _execute_press_key(self, key: str, **kwargs) -> Dict[str, Any]:
        """Нажать клавишу"""
        return await self.tools.press_key(key)

    async def _execute_type_text(self, selector: str, text: str, **kwargs) -> Dict[str, Any]:
        """Ввести текст в поле"""
        return await self.tools.type_text(selector, text)

    async def _execute_search_and_type(self, text: str, **kwargs) -> Dict[str, Any]:
        """Умный поиск: автоматически находит поле поиска и вводит текст"""
        # kwargs позволяет игнорировать неизвестные параметры (timeout и др.)
        return await self.tools.search_and_type(text)

    async def _execute_take_screenshot(self, filename: str = None, **kwargs) -> Dict[str, Any]:
        """Сделать скриншот"""
        return await self.tools.take_screenshot(filename)

    async def _execute_wait_for_text(self, text: str, timeout: int = 10000, **kwargs) -> Dict[str, Any]:
        """Дождаться появления текста"""
        return await self.tools.wait_for_text(text, timeout=timeout)

    async def _execute_find_text(self, search_text: str, **kwargs) -> Dict[str, Any]:
        """Найти текст на странице (Ctrl+F)"""
        return await self.tools.find_text_on_page(search_text)

    async def _execute_close_modal(self, **kwargs) -> Dict[str, Any]:
        """Закрыть модальное окно"""
        return await self.tools.close_modal()

    async def _execute_wait_for_modal(self, timeout: int = 5000, **kwargs) -> Dict[str, Any]:
        """Подождать появления модального окна"""
        return await self.tools.wait_for_modal(timeout=timeout)

    async def _execute_get_modal_text(self, **kwargs) -> Dict[str, Any]:
        """Получить текст из модального окна"""
        return await self.tools.get_modal_text()

    async def _execute_wait(self, seconds: float = 1.0, **kwargs) -> Dict[str, Any]:
        """Подождать указанное количество секунд"""
        import asyncio
        await asyncio.sleep(seconds)
        return {"status": "success", "message": f"Подождал {seconds} секунд"}

    async def _execute_scroll_to_text(self, text: str, highlight: bool = True, highlight_all: bool = False, **kwargs) -> Dict[str, Any]:
        """Прокрутить к тексту и подсветить элемент"""
        return await self.tools.scroll_to_text(text, highlight=highlight, highlight_all=highlight_all)

    # === КОНСТРУКТОР БЛЮД ===

    async def _execute_get_dish_customization_options(self, **kwargs) -> Dict[str, Any]:
        """Получить доступные опции кастомизации блюда"""
        return await self.tools.get_dish_customization_options()

    async def _execute_toggle_option(self, option_text: str, action: str = "select", **kwargs) -> Dict[str, Any]:
        """Переключить опцию (добавить/убрать/выбрать)"""
        return await self.tools.toggle_option(option_text, action=action)

    async def _execute_adjust_quantity(self, item_text: str, action: str, **kwargs) -> Dict[str, Any]:
        """Изменить количество ингредиента (increase/decrease)"""
        return await self.tools.adjust_quantity(item_text, action=action)

    async def _execute_select_size(self, size_text: str, **kwargs) -> Dict[str, Any]:
        """Выбрать размер блюда"""
        return await self.tools.select_size(size_text)

    async def _execute_done(self, message: str = None, **kwargs) -> Dict[str, Any]:
        """
        Завершить задачу и сообщить результат пользователю.

        Это специальное действие которое сигнализирует что агент
        закончил выполнение задачи и хочет сообщить результат.

        Args:
            message: Сообщение для пользователя с результатом

        Returns:
            Статус завершения с сообщением
        """
        return {
            "status": "done",
            "message": message or "Задача выполнена",
            "action_completed": True
        }

    def get_available_actions(self) -> list:
        """Получить список доступных действий"""
        return list(self.action_map.keys())
