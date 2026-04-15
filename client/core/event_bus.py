# core/event_bus.py
"""
Единая событийная шина - центральный узел коммуникации
"""
from typing import Dict, List, Callable, Any
from PySide6.QtCore import QObject, Signal
from enum import Enum, auto


class EventType(Enum):
    """Типы событий"""
    # Пользовательские события
    USER_TEXT_SUBMITTED = auto()
    USER_VOICE_PRESSED = auto()
    USER_CHIBI_CLICKED = auto()
    USER_CHIBI_DRAGGED = auto()

    
    # AI события
    TOOL_CALL_START = auto()
    TOOL_CALL_END = auto()
    AI_STREAM_START = auto()
    AI_TOKEN = auto()
    AI_STREAM_END = auto()
    AI_ERROR = auto()
    
    # UI события
    UI_SHOW_CHAT = auto()
    UI_HIDE_CHAT = auto()
    UI_SHOW_MESSAGE = auto()
    UI_HIDE_MESSAGE = auto()
    CHAT_PROCESSING_CHANGED = auto()
    
    # Чиби события
    CHIBI_WAKE_UP = auto()
    CHIBI_STATE_CHANGED = auto()
    CHIBI_POSITION_CHANGED = auto()
    CHIBI_ANIMATION_CHANGED = auto()
    
    # Событие обновления позиции UI элементов
    UI_UPDATE_POSITIONS = auto()


class Event:
    """Базовое событие"""
    def __init__(self, type: EventType, data: Any = None, source: Any = None):
        self.type = type
        self.data = data
        self.source = source
    
    def __repr__(self):
        return f"Event({self.type.name}, {self.data})"



class EventBus(QObject):
    """Шина событий с очередью"""
    
    event_emitted = Signal(Event)
    
    def __init__(self):
        super().__init__()
        self._handlers: Dict[EventType, List[Callable]] = {}
        self._event_queue: List[Event] = []
        self._processing = False
    
    def subscribe(self, event_type: EventType, handler: Callable):
        """Подписка на событие"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)

    
    def unsubscribe(self, event_type: EventType, handler: Callable):
        """Отписка от события"""
        if event_type in self._handlers and handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
    
    def emit(self, event: Event):
        """Отправка события - добавляем в очередь"""
        self._event_queue.append(event)
        self._process_queue()
    
    def _process_queue(self):
        """Обработка очереди событий"""
        if self._processing:
            return
        
        self._processing = True
        
        try:
            while self._event_queue:
                event = self._event_queue.pop(0)
                self._dispatch_event(event)
        finally:
            self._processing = False
    
    def _dispatch_event(self, event: Event):

        # Отправляем сигнал
        self.event_emitted.emit(event)
        
        # Вызываем обработчики
        if event.type in self._handlers:
            for handler in self._handlers[event.type]:
                try:
                    handler(event)
                except Exception as e:

                    import traceback
                    traceback.print_exc()