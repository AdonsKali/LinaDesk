import asyncio
import time


class RuntimeGate:
    def __init__(self):
        self.lock = asyncio.Lock()
        self.last_user_activity = time.monotonic()
        self.stopping = False

    def touch(self):
        self.last_user_activity = time.monotonic()

    def idle(self, seconds):
        return not self.stopping and not self.lock.locked() and (
            time.monotonic() - self.last_user_activity >= seconds
        )
