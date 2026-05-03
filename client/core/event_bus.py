from typing import Dict, List, Callable
from PySide6.QtCore import QObject, Signal
from .event_types import EventType
from .events import Event

class EventBus(QObject):
    """Центральная шина событий"""
    event_emitted = Signal(Event)
    
    def __init__(self):
        super().__init__()
        self._handlers: Dict[EventType, List[Callable]] = {}
        self._queue: List[Event] = []
        self._processing = False
    
    def subscribe(self, event_type: EventType, handler: Callable) -> None:
        """Подписка на событие"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)
    
    def unsubscribe(self, event_type: EventType, handler: Callable) -> None:
        """Отписка от события"""
        if event_type in self._handlers and handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
    
    def emit(self, event: Event) -> None:
        """Отправка события"""
        self._queue.append(event)
        self._process_queue()
    
    def _process_queue(self) -> None:
        """Обработка очереди событий"""
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
        """Диспетчеризация события"""
        self.event_emitted.emit(event)
        
        if event.type in self._handlers:
            for handler in self._handlers[event.type]:
                try:
                    handler(event)
                except Exception as e:
                    import traceback
                    traceback.print_exc()
