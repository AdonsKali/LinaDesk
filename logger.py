import datetime
from typing import Any, Literal

COLORS = {
    "info": "\033[92m",     # зеленый
    "error": "\033[91m",    # красный
    "warning": "\033[93m",  # жёлтый
    "debug": "\033[94m",    # синий
    "reset": "\033[0m"      # сброс цвета
}

LOG_FILE = "log.txt"

def log(message: Any, status: Literal['info','error','warning','debug'] = 'info', source: str = __name__):
    """_summary_

    Args:
        status (str): info, error, warning, debug, reset, tool
        source (str): default current module
        message (str): description
    """
    color = COLORS.get(status, COLORS["reset"])
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_console = f"{color}{status.upper()}{COLORS['reset']}: [{timestamp}]  {COLORS['debug']}[{source}]{COLORS['reset']}  {message}{COLORS['reset']}"
    formatted_file = f"{status.upper()}: [{timestamp}]  [{source}]  {message}"
    print(formatted_console)

    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(formatted_file + "\n")
    except Exception as e:
        print(f"{COLORS['error']}[LOGGER ERROR]{COLORS['reset']} Failed to write a log in file : {e}")