#!/usr/bin/env python3
"""
Real-time лог viewer с цветовой подсветкой.

Использование:
    python log_viewer.py [путь_к_лог_файлу]

Если путь не указан, используется последний файл из logs/execution_*.log
"""
import sys
import time
import re
from pathlib import Path
from datetime import datetime
from typing import Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from rich.console import Console
from rich.theme import Theme
from rich.text import Text

# Настройка темы для Rich
custom_theme = Theme({
    "info": "cyan",
    "success": "bold green",
    "error": "bold red",
    "warning": "yellow",
    "timestamp": "dim cyan",
    "function": "bold magenta",
    "file": "blue",
    "duration": "yellow",
})

console = Console(theme=custom_theme)


class LogLine:
    """Представление строки лога"""

    def __init__(self, raw_line: str):
        self.raw = raw_line.strip()
        self.timestamp = None
        self.level = None
        self.file_info = None
        self.function = None
        self.message = None
        self.duration = None

        self._parse()

    def _parse(self):
        """Парсинг строки лога"""
        # Формат: 2024-01-15 12:30:45 | INFO     | file.py:123 | func_name | message
        pattern = r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \| (\w+)\s+\| ([^|]+) \| ([^|]+) \| (.+)$'
        match = re.match(pattern, self.raw)

        if match:
            self.timestamp = match.group(1)
            self.level = match.group(2).strip()
            self.file_info = match.group(3).strip()
            self.function = match.group(4).strip()
            self.message = match.group(5).strip()

            # Извлекаем duration если есть
            duration_match = re.search(r'Duration: ([\d.]+)s', self.message)
            if duration_match:
                self.duration = float(duration_match.group(1))

    def to_rich_text(self) -> Text:
        """Преобразование в Rich Text с форматированием"""
        if not self.timestamp:
            # Если не удалось распарсить, возвращаем как есть
            return Text(self.raw, style="dim")

        text = Text()

        # Timestamp
        text.append(f"{self.timestamp} ", style="timestamp")

        # Level с иконками и цветами
        level_styles = {
            "INFO": ("ℹ️", "info"),
            "DEBUG": ("🔍", "dim"),
            "WARNING": ("⚠️", "warning"),
            "ERROR": ("❌", "error"),
        }

        # Специальные стили для START/SUCCESS/ERROR в сообщении
        if "⏯️  START" in self.message:
            text.append("⏯️  START ", style="bold cyan")
        elif "✅ SUCCESS" in self.message:
            text.append("✅ SUCCESS ", style="success")
        elif "❌ ERROR" in self.message:
            text.append("❌ ERROR ", style="error")
        else:
            icon, style = level_styles.get(self.level, ("", ""))
            text.append(f"{icon} {self.level:<8} ", style=style)

        # File info
        text.append(f"{self.file_info} ", style="file")

        # Function name
        text.append(f"[{self.function}] ", style="function")

        # Message
        # Подсветка duration
        msg = self.message
        if self.duration is not None:
            # Цвет в зависимости от длительности
            if self.duration < 0.1:
                duration_style = "green"
            elif self.duration < 1.0:
                duration_style = "yellow"
            else:
                duration_style = "red"

            msg = re.sub(
                r'(Duration: )([\d.]+s)',
                lambda m: f"{m.group(1)}",
                msg
            )
            parts = msg.split('Duration: ')
            if len(parts) == 2:
                text.append(parts[0])
                text.append("Duration: ", style="dim")
                text.append(f"{self.duration:.3f}s", style=duration_style)
                remaining = parts[1].split('s', 1)
                if len(remaining) > 1:
                    text.append(remaining[1])
            else:
                text.append(msg)
        else:
            text.append(msg)

        return text


class LogFileHandler(FileSystemEventHandler):
    """Обработчик изменений в лог-файле"""

    def __init__(self, log_path: Path, follow: bool = True):
        self.log_path = log_path
        self.follow = follow
        self.file_position = 0
        self.last_lines = []

        # Читаем существующий файл
        if self.log_path.exists():
            self._read_existing()

    def _read_existing(self):
        """Читаем существующий файл с начала"""
        console.print(f"\n[bold cyan]📂 Читаем файл: {self.log_path}[/bold cyan]\n")
        with open(self.log_path, 'r', encoding='utf-8') as f:
            for line in f:
                self._print_line(line)
            self.file_position = f.tell()

    def _print_line(self, line: str):
        """Печать строки с форматированием"""
        if line.strip():
            log_line = LogLine(line)
            console.print(log_line.to_rich_text())

    def _read_new_lines(self):
        """Читаем новые строки из файла"""
        if not self.log_path.exists():
            return

        with open(self.log_path, 'r', encoding='utf-8') as f:
            f.seek(self.file_position)
            new_lines = f.readlines()
            self.file_position = f.tell()

            for line in new_lines:
                self._print_line(line)

    def on_modified(self, event):
        """Обработка изменения файла"""
        if event.src_path == str(self.log_path):
            self._read_new_lines()


def get_latest_log_file(log_dir: Path = Path("logs")) -> Optional[Path]:
    """Получить последний лог-файл execution_*.log"""
    if not log_dir.exists():
        return None

    log_files = list(log_dir.glob("execution_*.log"))
    if not log_files:
        return None

    # Сортируем по времени модификации
    log_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return log_files[0]


def main():
    """Главная функция"""
    console.print("\n[bold green]🔍 Real-Time Log Viewer[/bold green]\n")

    # Определяем путь к лог-файлу
    if len(sys.argv) > 1:
        log_path = Path(sys.argv[1])
    else:
        log_path = get_latest_log_file()

    if log_path is None or not log_path.exists():
        console.print("[bold red]❌ Лог-файл не найден![/bold red]")
        console.print("\nИспользование:")
        console.print("  python log_viewer.py [путь_к_лог_файлу]")
        console.print("\nИли запустите агента для создания лог-файла:")
        console.print("  python main.py")
        sys.exit(1)

    # Создаём обработчик
    handler = LogFileHandler(log_path)

    # Настраиваем watchdog для отслеживания изменений
    observer = Observer()
    observer.schedule(handler, str(log_path.parent), recursive=False)
    observer.start()

    console.print(f"\n[bold cyan]👁️  Отслеживание: {log_path}[/bold cyan]")
    console.print("[dim]Нажмите Ctrl+C для выхода[/dim]\n")

    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        observer.stop()
        console.print("\n\n[bold yellow]👋 Log Viewer остановлен[/bold yellow]")

    observer.join()


if __name__ == "__main__":
    main()
