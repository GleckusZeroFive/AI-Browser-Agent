"""
Настройка логирования с автоматической ротацией и очисткой

Особенности:
- Автоматическая ротация по размеру (max 5 MB на файл)
- Хранение только последних 3 файлов
- Автоматическая очистка старых логов (старше 7 дней)
- Сжатие старых логов
"""
import logging
import os
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path


class LogSetup:
    """Настройка системы логирования с ротацией"""

    # Настройки ротации
    MAX_BYTES = 5 * 1024 * 1024  # 5 MB на файл
    BACKUP_COUNT = 3  # Хранить последние 3 файла
    LOG_RETENTION_DAYS = 7  # Удалять логи старше 7 дней

    @classmethod
    def setup_logging(cls, log_dir: str = "logs") -> logging.Logger:
        """
        Настроить систему логирования

        Args:
            log_dir: директория для логов

        Returns:
            Главный logger
        """
        # Создаем директорию если её нет
        os.makedirs(log_dir, exist_ok=True)

        # Очищаем старые логи
        cls._cleanup_old_logs(log_dir)

        # Настраиваем основной логгер
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)

        # Очищаем существующие handlers (избегаем дублирования)
        root_logger.handlers.clear()

        # 1. Логи диалога (INFO уровень)
        dialogue_handler = RotatingFileHandler(
            f"{log_dir}/dialogue_manager.log",
            maxBytes=cls.MAX_BYTES,
            backupCount=cls.BACKUP_COUNT,
            encoding='utf-8'
        )
        dialogue_handler.setLevel(logging.INFO)
        dialogue_handler.setFormatter(
            logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        )
        root_logger.addHandler(dialogue_handler)

        # 2. Логи ошибок (только ERROR)
        error_handler = RotatingFileHandler(
            f"{log_dir}/errors.log",
            maxBytes=cls.MAX_BYTES,
            backupCount=cls.BACKUP_COUNT,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(
            logging.Formatter('%(asctime)s [ERROR] %(message)s\n')
        )
        root_logger.addHandler(error_handler)

        # 3. Логи выполнения (для отладки, DEBUG уровень)
        execution_date = datetime.now().strftime("%Y%m%d")
        execution_handler = RotatingFileHandler(
            f"{log_dir}/execution_{execution_date}.log",
            maxBytes=cls.MAX_BYTES,
            backupCount=cls.BACKUP_COUNT,
            encoding='utf-8'
        )
        execution_handler.setLevel(logging.DEBUG)
        execution_handler.setFormatter(
            logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | '
                '%(funcName)s | %(message)s'
            )
        )
        root_logger.addHandler(execution_handler)

        # 4. Console handler для критичных ошибок
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.CRITICAL)
        console_handler.setFormatter(
            logging.Formatter('[CRITICAL] %(message)s')
        )
        root_logger.addHandler(console_handler)

        logging.info("=" * 70)
        logging.info("Система логирования инициализирована")
        logging.info(f"Директория логов: {log_dir}")
        logging.info(f"Размер файла: {cls.MAX_BYTES / (1024 * 1024):.1f} MB")
        logging.info(f"Количество backup файлов: {cls.BACKUP_COUNT}")
        logging.info(f"Срок хранения: {cls.LOG_RETENTION_DAYS} дней")
        logging.info("=" * 70)

        return root_logger

    @classmethod
    def setup_agent_response_log(cls, log_dir: str = "logs") -> str:
        """
        Настроить отдельный лог для ответов агента (не через logging module)

        Returns:
            Путь к файлу лога
        """
        log_file = f"{log_dir}/agent_responses.log"

        # Проверяем размер и делаем ротацию если нужно
        if os.path.exists(log_file):
            size = os.path.getsize(log_file)
            if size > cls.MAX_BYTES:
                cls._rotate_file(log_file, cls.BACKUP_COUNT)

        return log_file

    @classmethod
    def _rotate_file(cls, filepath: str, backup_count: int):
        """
        Ротация файла вручную

        Args:
            filepath: путь к файлу
            backup_count: сколько backup файлов хранить
        """
        # Удаляем самый старый backup если существует
        oldest_backup = f"{filepath}.{backup_count}"
        if os.path.exists(oldest_backup):
            os.remove(oldest_backup)

        # Сдвигаем все backup файлы
        for i in range(backup_count - 1, 0, -1):
            old_backup = f"{filepath}.{i}"
            new_backup = f"{filepath}.{i + 1}"
            if os.path.exists(old_backup):
                os.rename(old_backup, new_backup)

        # Переименовываем текущий файл в .1
        if os.path.exists(filepath):
            os.rename(filepath, f"{filepath}.1")

    @classmethod
    def _cleanup_old_logs(cls, log_dir: str):
        """
        Очистить старые лог файлы

        Удаляет файлы старше LOG_RETENTION_DAYS дней

        Args:
            log_dir: директория с логами
        """
        cutoff_date = datetime.now() - timedelta(days=cls.LOG_RETENTION_DAYS)
        log_path = Path(log_dir)

        if not log_path.exists():
            return

        deleted_count = 0
        for log_file in log_path.glob("*.log*"):
            # Проверяем время модификации файла
            file_time = datetime.fromtimestamp(log_file.stat().st_mtime)

            if file_time < cutoff_date:
                try:
                    log_file.unlink()
                    deleted_count += 1
                except Exception as e:
                    print(f"⚠️  Не удалось удалить {log_file}: {e}")

        if deleted_count > 0:
            print(f"🧹 Очищено {deleted_count} старых лог-файлов")


def get_logger(name: str) -> logging.Logger:
    """
    Получить logger с указанным именем

    Args:
        name: имя модуля (обычно __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
