from dataclasses import dataclass
from enum import Enum, auto
from http.client import PROCESSING


class ChibiState(Enum):
    """Состояния чиби"""
    IDLE = auto()
    TALKING = auto()
    THINKING = auto()
    LISTENING = auto()
    SLEEPING = auto()
    PROCESSING  = auto()


@dataclass
class Position:
    """Позиция на экране"""
    x: float = 0
    y: float = 0


@dataclass
class ChibiModel:
    """Модель чиби"""
    state: ChibiState = ChibiState.IDLE
    position: Position = Position(0, 0)
    current_animation: str = "idle"


@dataclass
class MessageModel:
    """Модель сообщения"""
    text: str = ""
    is_visible: bool = False


@dataclass
class ChatModel:
    """Модель чата"""
    is_visible: bool = False
    is_processing: bool = False
    input_text: str = ""