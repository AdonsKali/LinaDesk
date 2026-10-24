import asyncio
from typing import Dict, List, Callable, Any

from PySide6.QtCore import QObject, Signal

from .event_types import EventType
from .events import Event


class EventBus(QObject):
    """Центральная шина событий presentation-слоя (sync, Qt)."""

    event_emitted = Signal(Event)

    def __init__(self):
        super().__init__()
        self._handlers: Dict[EventType, List[Callable]] = {}
        self._queue: List[Event] = []
        self._processing = False

    def subscribe(self, event_type: EventType, handler: Callable) -> None:
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: EventType, handler: Callable) -> None:
        if event_type in self._handlers and handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)

    def emit(self, event: Event) -> None:
        self._queue.append(event)
        self._process_queue()

    def _process_queue(self) -> None:
        if self._processing:
            return
        self._processing = True
        try:
            while self._queue:
                event = self._queue.pop(0)
                self._dispatch(event)
        finally:
            self._processing = False

    def _dispatch(self, event: Event) -> None:
        self.event_emitted.emit(event)
        if event.type not in self._handlers:
            return

        for handler in self._handlers[event.type]:
            try:
                result = handler(event)
                # Поддержка async-хендлеров: если корутина — планируем в loop
                if asyncio.iscoroutine(result):
                    self._schedule_coroutine(result)
            except Exception:
                import traceback
                traceback.print_exc()

    @staticmethod
    def _schedule_coroutine(coro) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # Нет запущенного loop — просто закрываем корутину
            import logging
            logging.getLogger(__name__).warning(
                "No running asyncio loop; dropping coroutine %r", coro
            )
            coro.close()
            return
        loop.create_task(coro)