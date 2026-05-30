from PySide6.QtCore import Signal, Property, QTimer
from client.core.event_bus import EventBus
from client.core.events import Event
from client.core.event_types import EventType
from client.models.chat_model import MiniChatModel, ChatPosition
from client.viewmodels.base_viewmodel import BaseViewModel

class ChatViewModel(BaseViewModel):
    """ViewModel для чата"""
    
    visibility_changed = Signal(bool)
    processing_changed = Signal(bool)
    position_changed = Signal(int, int)  
    voice_state_changed = Signal(bool) 
    
    def __init__(self, event_bus: EventBus):
        super().__init__(event_bus)
        self._model = MiniChatModel()
        self._event_bus = event_bus
        self._updating = False
        
        self._hide_timer = QTimer()
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._auto_hide)
        self._hide_delay = 5000
        
        self.subscribe(EventType.CHAT_VISIBILITY_CHANGED, self._on_visibility_changed)
        self.subscribe(EventType.CHAT_PROCESSING_CHANGED, self._on_processing_changed)
        self.subscribe(EventType.CHAT_POSITION_UPDATED, self._on_position_changed)
        self.subscribe(EventType.ADD_TEXT_TO_PROMPT, self._on_add_text_to_prompt)
    
    @Property(bool, notify=visibility_changed)
    def is_visible(self) -> bool:
        return self._model.is_visible
    
    @Property(ChatPosition, notify=position_changed)
    def position(self) -> ChatPosition:
        return self._model.position
    
    @Property(bool, notify=processing_changed)
    def is_processing(self) -> bool:
        return self._model.is_processing
    
    def set_focus(self, has_focus: bool):
        """Установка фокуса на чате"""
        self._model.has_focus = has_focus
        if has_focus:
            self._hide_timer.stop()
        else:
            self._reset_hide_timer()
    
    def show(self):
        """Показать чат"""
        if not self._model.is_visible:
            self._model.is_visible = True
            self.visibility_changed.emit(True)
        self._reset_hide_timer()
    
    def hide(self):
        """Скрыть чат"""
        if self._model.is_visible:
            self._model.is_visible = False
            self.visibility_changed.emit(False)
    
    def _auto_hide(self):
        """Автоматическое скрытие"""
        if not self._model.has_focus and not self._model.is_processing:
            self.hide()
    
    def send_message(self, text: str):
        """Отправить сообщение"""
        if text.strip():
            self.emit(Event(EventType.USER_TEXT_SUBMITTED, {"text":text, "data_files":self._model._data_files}))
            self.emit(Event(EventType.CLEAR_ALL_FILE_STATUSES))
            self._model.clear_data_files()
    
    def start_voice(self):
        """Начать голосовой ввод"""
        if self._model.is_processing:
            return
        
        self._model.is_recording = True
        self.voice_state_changed.emit(True)
        self._event_bus.emit(Event(EventType.USER_VOICE_STARTED))


    def stop_voice(self):
        """Остановить голосовой ввод"""
        self._model.is_recording = False
        self.voice_state_changed.emit(False)
        self.emit(Event(EventType.USER_VOICE_STOPPED))
    
    def _reset_hide_timer(self):
        """Сброс таймера скрытия"""
        if not self._model.has_focus:
            self._hide_timer.start(self._hide_delay)
    
    def _on_position_changed(self, event: Event):
        """Обработка изменения позиции"""
        data = event.data
        self.position_changed.emit(data['x'], data['y'])
    
    def _on_visibility_changed(self, event: Event):
        if self._updating:
            return
        
        self._updating = True
        try:
            if event.data:
                self.show()
            else:
                self.hide()
        finally:
            self._updating = False
    
    def _on_processing_changed(self, event: Event):
        """Изменение статуса обработки"""
        if self._updating:
            return
        
        self._updating = True
        try:
            self._model.is_processing = event.data
            self.processing_changed.emit(self._model.is_processing)
            if not self._model.is_processing and not self._model.has_focus:
                self._reset_hide_timer()
        finally:
            self._updating = False

    def _on_add_text_to_prompt(self, event: Event):
        data = event.data
        self._model.add_data_files(data)