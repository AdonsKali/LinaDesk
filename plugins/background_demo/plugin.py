import time
from lina_plugin_sdk import report_progress


def wait(seconds):
    if not 1 <= seconds <= 60:
        raise ValueError("seconds must be between 1 and 60")
    for elapsed in range(1, seconds + 1):
        time.sleep(1)
        report_progress(100 * elapsed / seconds, f"Прошло {elapsed}/{seconds} секунд")
    return {"waited_seconds": seconds}
