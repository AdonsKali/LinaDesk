from PySide6.QtCore import QObject
from client.core.event_bus import EventBus
from client.core.events import Event
from client.core.event_types import EventType

class BaseViewModel(QObject):
    """Базовый класс для ViewModel"""
    
    def __init__(self, event_bus: EventBus):
        super().__init__()
        self._event_bus = event_bus
        self._subscribed = []
    
    def subscribe(self, event_type: EventType, handler) -> None:
        """Подписка на событие"""
        self._event_bus.subscribe(event_type, handler)
        self._subscribed.append((event_type, handler))
    
    def emit(self, event: Event) -> None:
        """Отправка события"""
        self._event_bus.emit(event)
    
    def unsubscribe_all(self) -> None:
        """Отписка от всех событий"""
        for event_type, handler in self._subscribed:
            self._event_bus.unsubscribe(event_type, handler)
        self._subscribed.clear()