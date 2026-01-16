"""
Demo Mode для AI Browser Agent.

Обеспечивает:
- Задержки между действиями
- Показ выполняемого кода
- Синхронизацию логов и действий
- Визуальные индикаторы
"""
import time
import asyncio
import inspect
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from functools import wraps
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel

from src.utils.logging_decorator import log_execution, log_async_execution


class DemoModeConfig:
    """Конфигурация Demo Mode"""

    def __init__(self, config_path: str = "demo_config.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Загрузить конфигурацию из YAML"""
        if not self.config_path.exists():
            # Возвращаем стандартные настройки
            return {
                "demo_mode": {
                    "enabled": False,
                    "delays": {
                        "before_action": 0.0,
                        "after_action": 0.0,
                        "visual_indicator": 0.5,
                        "code_to_action": 0.0,
                    },
                    "visual_markers": {"enabled": False},
                    "logging": {
                        "level": "normal",
                        "show_code_line": False,
                        "show_function_name": True,
                        "show_arguments": False,
                        "show_duration": False,
                        "colorized_console": True,
                    },
                }
            }

        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    @property
    def enabled(self) -> bool:
        """Включен ли demo mode"""
        return self.config.get("demo_mode", {}).get("enabled", False)

    @property
    def delays(self) -> Dict[str, float]:
        """Задержки"""
        return self.config.get("demo_mode", {}).get("delays", {})

    @property
    def visual_markers_enabled(self) -> bool:
        """Включены ли визуальные маркеры"""
        return self.config.get("demo_mode", {}).get("visual_markers", {}).get("enabled", False)

    @property
    def logging_config(self) -> Dict[str, Any]:
        """Конфигурация логирования"""
        return self.config.get("demo_mode", {}).get("logging", {})


class DemoMode:
    """Менеджер Demo Mode"""

    def __init__(self, config: Optional[DemoModeConfig] = None):
        self.config = config or DemoModeConfig()
        self.console = Console()
        self._action_counter = 0

    @property
    def enabled(self) -> bool:
        """Включен ли demo mode"""
        return self.config.enabled

    async def before_action(self, func_name: str, args: tuple, kwargs: dict):
        """
        Выполняется перед действием.

        - Показывает код функции
        - Делает задержку
        - Выводит информацию о действии
        """
        if not self.enabled:
            return

        self._action_counter += 1

        # Показываем информацию о действии
        action_info = self._format_action_info(func_name, args, kwargs)
        self.console.print(action_info)

        # Показываем код если нужно
        if self.config.logging_config.get("show_code_line", True):
            self._show_code_context(func_name)

        # Задержка перед действием
        delay = self.config.delays.get("before_action", 1.0)
        if delay > 0:
            await asyncio.sleep(delay)

    async def after_action(self, func_name: str, result: Any, duration: float):
        """
        Выполняется после действия.

        - Показывает результат
        - Делает задержку
        """
        if not self.enabled:
            return

        # Показываем результат если нужно
        if self.config.logging_config.get("show_duration", True):
            self.console.print(f"[dim]⏱️  Выполнено за {duration:.3f}s[/dim]\n")

        # Задержка после действия
        delay = self.config.delays.get("after_action", 0.5)
        if delay > 0:
            await asyncio.sleep(delay)

    def _format_action_info(self, func_name: str, args: tuple, kwargs: dict) -> Panel:
        """Форматировать информацию о действии"""
        # Заголовок
        title = f"[bold cyan]Действие #{self._action_counter}[/bold cyan]"

        # Содержимое
        content = f"[bold yellow]Функция:[/bold yellow] {func_name}\n"

        if self.config.logging_config.get("show_arguments", True) and (args or kwargs):
            args_str = ", ".join(repr(arg) for arg in args)
            kwargs_str = ", ".join(f"{k}={v!r}" for k, v in kwargs.items())
            signature = ", ".join(filter(None, [args_str, kwargs_str]))
            if len(signature) > 100:
                signature = signature[:100] + "..."
            content += f"[bold yellow]Аргументы:[/bold yellow] {signature}\n"

        return Panel(content, title=title, border_style="cyan")

    def _show_code_context(self, func_name: str):
        """Показать контекст кода функции"""
        try:
            # Получаем frame вызывающей функции
            frame = inspect.currentframe()
            if frame and frame.f_back and frame.f_back.f_back:
                caller_frame = frame.f_back.f_back
                filename = caller_frame.f_code.co_filename
                lineno = caller_frame.f_lineno

                # Читаем код
                with open(filename, 'r', encoding='utf-8') as f:
                    lines = f.readlines()

                # Берём несколько строк контекста
                start = max(0, lineno - 3)
                end = min(len(lines), lineno + 2)
                code_lines = "".join(lines[start:end])

                # Показываем с подсветкой синтаксиса
                syntax = Syntax(
                    code_lines,
                    "python",
                    theme="monokai",
                    line_numbers=True,
                    start_line=start + 1,
                    highlight_lines={lineno},
                )

                self.console.print(Panel(syntax, title=f"[bold green]Код[/bold green] ({Path(filename).name}:{lineno})", border_style="green"))

        except Exception as e:
            # Игнорируем ошибки показа кода
            pass

    async def delay(self, delay_type: str):
        """
        Сделать задержку определённого типа.

        Args:
            delay_type: Тип задержки (before_action, after_action, visual_indicator, code_to_action)
        """
        if not self.enabled:
            return

        delay = self.config.delays.get(delay_type, 0.0)
        if delay > 0:
            await asyncio.sleep(delay)


# Глобальный экземпляр
_demo_mode_instance: Optional[DemoMode] = None


def get_demo_mode(config: Optional[DemoModeConfig] = None) -> DemoMode:
    """Получить глобальный экземпляр DemoMode"""
    global _demo_mode_instance
    if _demo_mode_instance is None:
        _demo_mode_instance = DemoMode(config)
    return _demo_mode_instance


def demo_action(func: Callable) -> Callable:
    """
    Декоратор для действий агента в demo mode.

    Автоматически:
    - Логирует выполнение
    - Показывает код
    - Делает задержки
    - Включает визуальные маркеры
    """
    # Применяем log_execution
    logged_func = log_execution(func)

    @wraps(func)
    def wrapper(*args, **kwargs):
        demo = get_demo_mode()

        if not demo.enabled:
            # Если demo mode выключен, просто вызываем функцию
            return logged_func(*args, **kwargs)

        # Demo mode включен
        import asyncio

        # Проверяем, есть ли event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Before action
        loop.run_until_complete(demo.before_action(func.__name__, args, kwargs))

        # Выполняем функцию
        start_time = time.perf_counter()
        result = logged_func(*args, **kwargs)
        duration = time.perf_counter() - start_time

        # After action
        loop.run_until_complete(demo.after_action(func.__name__, result, duration))

        return result

    return wrapper


def demo_async_action(func: Callable) -> Callable:
    """
    Декоратор для асинхронных действий агента в demo mode.
    """
    # Применяем log_async_execution
    logged_func = log_async_execution(func)

    @wraps(func)
    async def wrapper(*args, **kwargs):
        demo = get_demo_mode()

        if not demo.enabled:
            # Если demo mode выключен, просто вызываем функцию
            return await logged_func(*args, **kwargs)

        # Demo mode включен
        # Before action
        await demo.before_action(func.__name__, args, kwargs)

        # Выполняем функцию
        start_time = time.perf_counter()
        result = await logged_func(*args, **kwargs)
        duration = time.perf_counter() - start_time

        # After action
        await demo.after_action(func.__name__, result, duration)

        return result

    return wrapper


def initialize_demo_mode(enabled: bool = False):
    """
    Инициализировать demo mode.

    Args:
        enabled: Включить demo mode (переопределяет config)
    """
    global _demo_mode_instance
    config = DemoModeConfig()

    # Переопределяем enabled из аргумента
    if enabled:
        config.config["demo_mode"]["enabled"] = True

    _demo_mode_instance = DemoMode(config)

    if _demo_mode_instance.enabled:
        print("\n" + "="*70)
        print("🎬 DEMO MODE ВКЛЮЧЕН")
        print("="*70)
        print(f"Задержки: {config.delays}")
        print(f"Визуальные маркеры: {config.visual_markers_enabled}")
        print(f"Логирование: {config.logging_config.get('level', 'normal')}")
        print("="*70 + "\n")
