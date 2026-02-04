from enum import Enum, auto
from PySide6.QtCore import QObject, Signal

class LinaState(Enum):
    IDLE = auto()
    LISTENING = auto()
    THINKING = auto()
    WALKING = auto()
    TALKING = auto()


class LinaStateMachine(QObject):
    state_changed = Signal(LinaState)

    def __init__(self):
        super().__init__()
        self._state = LinaState.IDLE

    @property
    def state(self):
        return self._state

    def set_state(self, new_state: LinaState):
        if self._state != new_state:
            self._state = new_state
            self.state_changed.emit(new_state)