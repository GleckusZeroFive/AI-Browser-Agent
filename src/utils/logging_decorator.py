"""
Декоратор для логирования выполнения функций агента.

Использование:
    @log_execution
    def my_function(arg1, arg2):
        ...
"""
import functools
import inspect
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Any


class ExecutionLogger:
    """Централизованный логгер для выполнения функций агента"""

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        # Создаём отдельный логгер для execution
        self.logger = logging.getLogger("execution_logger")
        self.logger.setLevel(logging.DEBUG)

        # Удаляем существующие handlers чтобы избежать дублирования
        self.logger.handlers.clear()

        # File handler для детального лога
        log_file = self.log_dir / f"execution_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)

        # Console handler для важных событий
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # Формат лога
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(funcName)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

        # Не пропагируем в root logger
        self.logger.propagate = False

    def log_execution(self, func: Callable) -> Callable:
        """
        Декоратор для логирования выполнения функции.

        Логирует:
        - Имя файла и номер строки
        - Имя функции
        - Переданные аргументы
        - Время начала и окончания
        - Время выполнения
        - Результат выполнения или ошибку
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Получаем информацию о функции
            frame = inspect.currentframe()
            caller_frame = frame.f_back if frame else None

            # Информация о месте вызова
            file_info = inspect.getfile(func)
            file_name = Path(file_info).name
            line_no = func.__code__.co_firstlineno

            # Форматируем аргументы
            args_repr = [repr(a) for a in args]
            kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
            signature = ", ".join(args_repr + kwargs_repr)

            # Начало выполнения
            self.logger.info(f"⏯️  START | {file_name}:{line_no} | {func.__name__}({signature})")
            start_time = time.perf_counter()

            try:
                # Выполняем функцию
                result = func(*args, **kwargs)

                # Конец выполнения
                end_time = time.perf_counter()
                duration = end_time - start_time

                # Логируем успешное завершение
                result_repr = repr(result) if result is not None else "None"
                if len(result_repr) > 200:
                    result_repr = result_repr[:200] + "..."

                self.logger.info(
                    f"✅ SUCCESS | {file_name}:{line_no} | {func.__name__} | "
                    f"Duration: {duration:.3f}s | Result: {result_repr}"
                )

                return result

            except Exception as e:
                # Конец выполнения с ошибкой
                end_time = time.perf_counter()
                duration = end_time - start_time

                # Логируем ошибку
                self.logger.error(
                    f"❌ ERROR | {file_name}:{line_no} | {func.__name__} | "
                    f"Duration: {duration:.3f}s | Error: {type(e).__name__}: {str(e)}"
                )

                raise

        return wrapper

    def log_async_execution(self, func: Callable) -> Callable:
        """
        Декоратор для логирования асинхронных функций.
        """
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Получаем информацию о функции
            file_info = inspect.getfile(func)
            file_name = Path(file_info).name
            line_no = func.__code__.co_firstlineno

            # Форматируем аргументы
            args_repr = [repr(a) for a in args]
            kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
            signature = ", ".join(args_repr + kwargs_repr)

            # Начало выполнения
            self.logger.info(f"⏯️  START (async) | {file_name}:{line_no} | {func.__name__}({signature})")
            start_time = time.perf_counter()

            try:
                # Выполняем async функцию
                result = await func(*args, **kwargs)

                # Конец выполнения
                end_time = time.perf_counter()
                duration = end_time - start_time

                # Логируем успешное завершение
                result_repr = repr(result) if result is not None else "None"
                if len(result_repr) > 200:
                    result_repr = result_repr[:200] + "..."

                self.logger.info(
                    f"✅ SUCCESS (async) | {file_name}:{line_no} | {func.__name__} | "
                    f"Duration: {duration:.3f}s | Result: {result_repr}"
                )

                return result

            except Exception as e:
                # Конец выполнения с ошибкой
                end_time = time.perf_counter()
                duration = end_time - start_time

                # Логируем ошибку
                self.logger.error(
                    f"❌ ERROR (async) | {file_name}:{line_no} | {func.__name__} | "
                    f"Duration: {duration:.3f}s | Error: {type(e).__name__}: {str(e)}"
                )

                raise

        return wrapper


# Создаём глобальный экземпляр логгера
_execution_logger = ExecutionLogger()

# Экспортируем декораторы
log_execution = _execution_logger.log_execution
log_async_execution = _execution_logger.log_async_execution


# Для совместимости: функция, возвращающая декоратор
def get_execution_logger() -> ExecutionLogger:
    """Получить экземпляр ExecutionLogger"""
    return _execution_logger
