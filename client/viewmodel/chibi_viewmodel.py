from PySide6.QtCore import QObject, Signal, Property
from core.event_bus import EventBus, Event, EventType


class ChibiViewModel(QObject):
    """ViewModel для чиби"""
    
    state_changed = Signal(str)
    position_changed = Signal(int, int)
    animation_changed = Signal(str)
    
    def __init__(self, event_bus: EventBus):
        super().__init__()
        self._event_bus = event_bus
        self._state = "IDLE"
        self._position = (0, 0)
        self._animation = "idle"
        self._updating = False  # Защита от рекурсии
        
        # Подписка на события
        event_bus.subscribe(EventType.CHIBI_STATE_CHANGED, self._on_state_changed)
        event_bus.subscribe(EventType.CHIBI_POSITION_CHANGED, self._on_position_changed)
        event_bus.subscribe(EventType.CHIBI_ANIMATION_CHANGED, self._on_animation_changed)
    
    @Property(str, notify=state_changed)
    def state(self) -> str:
        return self._state
    
    @Property(str, notify=animation_changed)
    def animation(self) -> str:
        return self._animation
    
    def wake_up(self):
        """Пробуждение"""
        self._event_bus.emit(Event(EventType.USER_CHIBI_CLICKED))
    
    def on_dragged(self, x: float, y: float):
        """Перетаскивание"""
        self._event_bus.emit(Event(EventType.USER_CHIBI_DRAGGED, (x, y)))
    
    def _on_state_changed(self, event: Event):
        if self._updating:
            return
        
        self._updating = True
        try:
            self._state = event.data
            self.state_changed.emit(self._state)
        finally:
            self._updating = False
    
    def _on_position_changed(self, event: Event):
        if self._updating:
            return
        
        self._updating = True
        try:
            x, y = event.data
            self._position = (x, y)
            self.position_changed.emit(int(x), int(y))
        finally:
            self._updating = False
    
    def _on_animation_changed(self, event: Event):
        if self._updating:
            return
        
        self._updating = True
        try:
            self._animation = event.data
            self.animation_changed.emit(self._animation)
        finally:
            self._updating = False