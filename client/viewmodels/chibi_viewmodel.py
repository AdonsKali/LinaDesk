from PySide6.QtCore import Signal, Property
from client.core.event_bus import EventBus
from client.core.events import Event
from client.core.event_types import EventType
from client.models.chibi_model import ChibiModel, ChibiState, AnimationType
from .base_viewmodel import BaseViewModel

class ChibiViewModel(BaseViewModel):
    """ViewModel для управления чиби персонажем"""
    
    state_changed = Signal(str)
    animation_changed = Signal(str)
    position_changed = Signal(int, int)
    
    def __init__(self, event_bus: EventBus):
        super().__init__(event_bus)
        self._model = ChibiModel()
        
        self.subscribe(EventType.CHIBI_STATE_CHANGED, self._on_state_changed)
        self.subscribe(EventType.CHIBI_ANIMATION_CHANGED, self._on_animation_changed)
        self.subscribe(EventType.CHIBI_POSITION_CHANGED, self._on_position_changed)
    
    @Property(str, notify=state_changed)
    def state(self) -> str:
        return self._model.state.name
    
    @Property(str, notify=animation_changed)
    def animation(self) -> str:
        return self._model.animation.value
    
    def on_clicked(self) -> None:
        """Обработка клика по чиби"""
        if self._model.state == ChibiState.SLEEPING:
            self._update_state(ChibiState.IDLE, AnimationType.IDLE)
        
        self.emit(Event(EventType.USER_CHIBI_CLICKED))
    
    def on_dragged(self, x: int, y: int) -> None:
        """Обработка перетаскивания"""
        self._model.update_position(x, y)
        self.emit(Event(EventType.CHIBI_POSITION_CHANGED, (x, y)))
        self.emit(Event(EventType.USER_CHIBI_DRAGGED, (x, y)))
    
    def _update_state(self, state: ChibiState, animation: AnimationType) -> None:
        """Обновление состояния модели"""
        self._model.update_state(state, animation)
        self.state_changed.emit(state.name)
        self.animation_changed.emit(animation.value)
    
    def _on_state_changed(self, event: Event) -> None:
        """Обработчик изменения состояния"""
        state_name = event.data
        if state_name in ChibiState.__members__:
            state = ChibiState[state_name]
            if state == ChibiState.THINKING:
                self._update_state(state, AnimationType.THINK)
            elif state == ChibiState.TALKING:
                self._update_state(state, AnimationType.TALK)
            elif state == ChibiState.PROCESSING:
                self._update_state(state, AnimationType.PROCESS)
            else:
                self._update_state(state, AnimationType.IDLE)
    
    def _on_animation_changed(self, event: Event) -> None:
        """Обработчик изменения анимации"""
        animation_name = event.data
        if animation_name in [a.value for a in AnimationType]:
            self.animation_changed.emit(animation_name)
    
    def _on_position_changed(self, event: Event) -> None:
        """Обработчик изменения позиции"""
        x, y = event.data
        self.position_changed.emit(int(x), int(y))
