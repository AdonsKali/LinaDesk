import random
from PySide6.QtCore import QObject, Signal, Property, QTimer
from ..core.event_bus import EventBus
from ..core.events import Event
from ..core.event_types import EventType
from ..models.message_model import BubbleModel, BubblePosition
from .base_viewmodel import BaseViewModel
import logging

log = logging.getLogger(__name__)

class BubbleViewModel(BaseViewModel):
    """ViewModel для облачка с сообщением"""
    
    visibility_changed = Signal(bool)
    text_changed = Signal(str)
    position_changed = Signal(str)
    position_coordinates_changed = Signal(int, int)
    
    def __init__(self, event_bus: EventBus):
        super().__init__(event_bus)
        self._model = BubbleModel()
        self._hide_timer = QTimer()
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)
        self._hide_delay = 8000
        self._updating = False

        self.subscribe(EventType.BUBBLE_VISIBILITY_CHANGED, self._on_visibility_changed)
        self.subscribe(EventType.BUBBLE_TEXT_CHANGED, self._on_text_changed)
        self.subscribe(EventType.BUBBLE_POSITION_UPDATED, self._on_position_updated)
        self.subscribe(EventType.USER_CHIBI_CLICKED, self._on_chibi_clicked)
        
        self.wake_up_texts = [
            self.tr("All ears!"),
            self.tr("Ah? Yes, I'm listening..."),
            self.tr("What task lies before me?"),
            self.tr("Ready to work and communicate with you.")
        ]
    
    @Property(str, notify=position_changed)
    def position(self) -> str:
        return self._model.position.value if self._model.position else "left-bottom"
    
    @Property(bool, notify=visibility_changed)
    def is_visible(self) -> bool:
        return self._model.is_visible
    
    @Property(str, notify=text_changed)
    def text(self) -> str:
        return self._model.text
    
    def show(self, text: str | None = None, delay: int | None = None):
        """Показать облачко"""
        if self._is_cleaned:
            return
        
        if delay is None:
            delay = self._hide_delay
        
        if text is not None:
            self._model.text = text
            self.text_changed.emit(text)
        
        if not self._model.is_visible:
            self._model.is_visible = True
            self.visibility_changed.emit(True)
        
        if self._hide_timer:
            self._hide_timer.start(delay)
    
    def hide(self):
        """Скрыть облачко"""
        if self._is_cleaned:
            return
            
        if self._model.is_visible:
            self._model.is_visible = False
            self._model.text = ""
            self.visibility_changed.emit(False)
            self.text_changed.emit("")
    
    def append_token(self, token: str):
        """Добавление токена"""
        if self._is_cleaned:
            return
            
        self._model.text += token
        self.text_changed.emit(self._model.text)
        if self._hide_timer:
            self._hide_timer.start(self._hide_delay)
        
        if not self._model.is_visible:
            self.show()
    
    def _on_position_updated(self, event: Event):
        """Обработка обновления позиции"""
        if self._is_cleaned or self._updating:
            return
        
        self._updating = True
        try:
            data = event.data
            x, y = data['x'], data['y']
            position_type = data.get('type', 'left-bottom')
            
            if self._model.position.value != position_type:
                self._model.position = BubblePosition(position_type)
                self.position_changed.emit(position_type)
            
            self.position_coordinates_changed.emit(x, y)
        finally:
            self._updating = False
    
    def _on_visibility_changed(self, event: Event):
        if self._is_cleaned or self._updating:
            return
        self._updating = True
        try:
            if event.data:
                self.show()
            else:
                self.hide()
        finally:
            self._updating = False
    
    def _on_text_changed(self, event: Event):
        if self._is_cleaned or self._updating:
            return
        self._updating = True
        try:
            if event.data:
                self._model.text = event.data
                self.text_changed.emit(event.data)
        finally:
            self._updating = False
    
    def _on_chibi_clicked(self, event: Event):
        """Show a random wake-up text when chibi is clicked"""
        if self._is_cleaned:
            return
        random_text = random.choice(self.wake_up_texts)
        self.show(random_text)
    
    def cleanup(self):
        """Очистка ресурсов"""
        if self._is_cleaned:
            return
        
        log.info("Cleaning up BubbleViewModel...")
        
        # Останавливаем таймер
        if self._hide_timer:
            self._hide_timer.stop()
            try:
                self._hide_timer.timeout.disconnect()
            except:
                pass
            self._hide_timer.setParent(None)
            self._hide_timer.deleteLater()
            self._hide_timer = None
        
        # Очищаем модель
        self._model = None
        
        # Вызываем родительский cleanup
        super().cleanup()