import datetime
from typing import Any, Literal
from pathlib import Path
import shutil


COLORS = {
    "info": "\033[92m",      # зелёный
    "error": "\033[91m",     # красный
    "warning": "\033[93m",   # жёлтый
    "debug": "\033[94m",     # синий
    "critical": "\033[95m",  # фиолетовый
    "reset": "\033[0m"       # сброс
}
LOG_DIR = Path("./logs")
LOG_DIR.mkdir(exist_ok=True)
_current_app = "app"


def clear_logs():
    """
    Очистка директории с логами
    """
    if LOG_DIR.exists():
        for item in LOG_DIR.iterdir():
            if item.is_file() and item.suffix == '.log':
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
        print(f"{COLORS['info']}LOGS CLEARED{COLORS['reset']} [{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] - All logs cleared from {LOG_DIR}")
    else:
        print(f"Log directory does not exist: {LOG_DIR}")


def setup(app_name: str, log_dir: str = "./logs", debug: bool = False, clear_on_start: bool = False):
    """
    Настройка логирования для конкретного приложения.
    """
    global _current_app, LOG_DIR
    _current_app = app_name
    LOG_DIR = Path(log_dir)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    if clear_on_start:
        clear_logs()
    log(f"Logger initialized for '{app_name}'", 'info', 'logger')


def _get_log_file(status: str = 'info') -> Path:
    """Получить путь к файлу лога"""
    if status in ('error', 'critical'):
        return LOG_DIR / f"{_current_app}_error.log"
    return LOG_DIR / f"{_current_app}.log"


def log(message: Any, 
        status: Literal['info', 'error', 'warning', 'debug', 'critical'] = 'info', 
        source: str | None = None):
    """
    Логирование сообщения в консоль и файл.
    """
    if source is None:
        source = _current_app
    
    color = COLORS.get(status, COLORS["reset"])
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_console = (
        f"{color}{status.upper():7s}{COLORS['reset']} "
        f"[{timestamp}]  "
        f"{COLORS['debug']}[{source}]{COLORS['reset']}  "
        f"{message}"
    )
    
    formatted_file = f"{status.upper():7s} [{timestamp}]  [{source}]  {message}"
    print(formatted_console)
    try:
        log_file = _get_log_file(status)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(formatted_file + "\n")
    except Exception as e:
        print(f"{COLORS['error']}[LOGGER ERROR]{COLORS['reset']} Failed to write log: {e}")


def get_logger(source: str):
    """
    Получить логгер привязанный к источнику.
    """
    class Logger:
        def info(self, msg): log(msg, 'info', source)
        def error(self, msg): log(msg, 'error', source)
        def warning(self, msg): log(msg, 'warning', source)
        def debug(self, msg): log(msg, 'debug', source)
        def critical(self, msg): log(msg, 'critical', source)
    return Logger()
