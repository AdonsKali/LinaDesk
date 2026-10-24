from dataclasses import dataclass
from enum import Enum, auto
from typing import Tuple

class ChibiState(Enum):
    """Состояния чиби персонажа"""
    IDLE = auto()
    TALKING = auto()
    THINKING = auto()
    LISTENING = auto()
    PROCESSING = auto()
    SLEEPING = auto()

class AnimationType(Enum):
    """Типы анимаций"""
    IDLE = "idle"
    TALK = "talk"
    THINK = "think"
    PROCESS = "process"
    FILE_DROPPED = "file_dropped"

@dataclass
class ChibiModel:
    """Модель чиби персонажа"""
    state: ChibiState = ChibiState.IDLE
    animation: AnimationType = AnimationType.IDLE
    position: Tuple[int, int] = (100, 100)
    is_dragging: bool = False
    
    def update_state(self, state: ChibiState, animation: AnimationType) -> 'ChibiModel':
        """Обновление состояния"""
        self.state = state
        self.animation = animation
        return self
    
    def update_position(self, x: int, y: int) -> 'ChibiModel':
        """Обновление позиции"""
        self.position = (x, y)
        return self