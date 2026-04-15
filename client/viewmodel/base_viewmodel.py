from PySide6.QtCore import QObject
from core.event_bus import EventBus, Event, EventType


class BaseViewModel(QObject):
    """Базовый класс для всех ViewModel"""
    
    def __init__(self, event_bus: EventBus):
        super().__init__()
        self._event_bus = event_bus
    

    def subscribe(self, event_type: EventType, handler):
        """Подписка на событие"""
        self._event_bus.subscribe(event_type, handler)
    
    def emit(self, event: Event):
        """Отправить событие"""
        self._event_bus.emit(event)