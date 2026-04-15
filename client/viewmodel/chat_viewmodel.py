from PySide6.QtCore import QObject, Signal, Property
from core.event_bus import EventBus, Event, EventType


class ChatViewModel(QObject):
    """ViewModel для чата"""
    
    visibility_changed = Signal(bool)
    processing_changed = Signal(bool)
    
    def __init__(self, event_bus: EventBus):
        super().__init__()
        self._event_bus = event_bus
        self._is_visible = False
        self._is_processing = False
        self._updating = False  # Защита от рекурсии
        
        # Подписка на события
        event_bus.subscribe(EventType.UI_SHOW_CHAT, self._on_show)
        event_bus.subscribe(EventType.UI_HIDE_CHAT, self._on_hide)
        event_bus.subscribe(EventType.CHAT_PROCESSING_CHANGED, self._on_processing_changed)
    
    @Property(bool, notify=visibility_changed)
    def is_visible(self) -> bool:
        return self._is_visible
    
    @Property(bool, notify=processing_changed)
    def is_processing(self) -> bool:
        return self._is_processing
    
    def send_message(self, text: str):
        """Отправить сообщение"""
        if text.strip():
            self._event_bus.emit(Event(EventType.USER_TEXT_SUBMITTED, text))
    
    def start_voice(self):
        """Начать голосовой ввод"""
        self._event_bus.emit(Event(EventType.USER_VOICE_PRESSED))
    
    def _on_show(self, event: Event):
        """Показать чат"""
        if self._updating:
            return
        
        self._updating = True
        try:
            if not self._is_visible:
                self._is_visible = True
                self.visibility_changed.emit(True)
        finally:
            self._updating = False
    
    def _on_hide(self, event: Event):
        """Скрыть чат"""
        if self._updating:
            return
        
        self._updating = True
        try:
            if self._is_visible:
                self._is_visible = False
                self.visibility_changed.emit(False)
        finally:
            self._updating = False
    
    def _on_processing_changed(self, event: Event):
        """Изменение статуса обработки"""
        if self._updating:
            return
        
        self._updating = True
        try:
            self._is_processing = event.data
            self.processing_changed.emit(self._is_processing)
        finally:
            self._updating = False