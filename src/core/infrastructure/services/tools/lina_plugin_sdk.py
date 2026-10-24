import json
import math
import sys
import threading
import time

_lock = threading.Lock()
_last_report = 0.0


def report_progress(percent, message=""):
    """Report progress without invoking the LLM; at most four updates per second."""
    global _last_report
    if isinstance(percent, bool) or not isinstance(percent, (int, float)) or not math.isfinite(percent) or not 0 <= percent <= 100:
        raise ValueError("Progress must be between 0 and 100")
    with _lock:
        now = time.monotonic()
        if now - _last_report < .25 and percent != 100:
            return
        _last_report = now
        sys.__stdout__.write(json.dumps(dict(type="progress", progress=percent, message=str(message)[:300]), ensure_ascii=False) + "\n")
        sys.__stdout__.flush()
