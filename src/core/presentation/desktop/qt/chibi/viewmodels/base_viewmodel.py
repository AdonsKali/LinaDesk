from PySide6.QtCore import QObject
from ..core.event_bus import EventBus
from ..core.events import Event
from ..core.event_types import EventType
import logging

log = logging.getLogger(__name__)

class BaseViewModel(QObject):
    """Базовый класс для ViewModel"""
    
    def __init__(self, event_bus: EventBus):
        super().__init__()
        self._event_bus = event_bus
        self._subscribed = []
        self._is_cleaned = False
    
    def subscribe(self, event_type: EventType, handler) -> None:
        """Подписка на событие"""
        if self._is_cleaned:
            log.warning(f"Attempting to subscribe to {event_type} after cleanup")
            return
        self._event_bus.subscribe(event_type, handler)
        self._subscribed.append((event_type, handler))
    
    def emit(self, event: Event) -> None:
        """Отправка события"""
        if self._is_cleaned:
            return
        self._event_bus.emit(event)
    
    def unsubscribe_all(self) -> None:
        """Отписка от всех событий"""
        for event_type, handler in self._subscribed:
            try:
                self._event_bus.unsubscribe(event_type, handler)
            except Exception as e:
                log.error(f"Error unsubscribing from {event_type}: {e}")
        self._subscribed.clear()
    
    def cleanup(self):
        """Очистка ресурсов - переопределить в наследниках"""
        if self._is_cleaned:
            return
        
        self._is_cleaned = True
        log.info(f"Cleaning up {self.__class__.__name__}...")
        
        # Отписываемся от всех событий
        self.unsubscribe_all()
        
        # Удаляем все дочерние объекты
        for child in self.children():
            try:
                child.setParent(None)
                child.deleteLater()
            except:
                pass
        
        self._event_bus = None
        import gc
        gc.collect()