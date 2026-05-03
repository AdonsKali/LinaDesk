from PySide6.QtCore import QObject
from client.core.event_bus import EventBus

class BaseService(QObject):
    """Базовый класс для сервисов"""
    
    def __init__(self, event_bus: EventBus):
        super().__init__()
        self._event_bus = event_bus
    
    def initialize(self) -> None:
        """Инициализация сервиса (переопределить в наследниках)"""
        pass
    
    def cleanup(self) -> None:
        """Очистка ресурсов (переопределить в наследниках)"""
        pass