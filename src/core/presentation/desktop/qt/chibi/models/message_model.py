from dataclasses import dataclass
from enum import Enum, auto

class MessageSource(Enum):
    """Источник сообщения"""
    USER = auto()
    AI = auto()
    SYSTEM = auto()


class BubblePosition(Enum):
    """Позиция облачка относительно чиби"""
    RIGHT_TOP = "right-top"
    LEFT_TOP = "left-top"
    RIGHT_BOTTOM = "right-bottom"
    LEFT_BOTTOM = "left-bottom"



@dataclass
class BubbleModel:
    """Модель сообщения"""
    is_streaming: bool = False
    is_visible: bool = False
    source: MessageSource = MessageSource.AI
    position: BubblePosition = BubblePosition.RIGHT_TOP
    text: str = ""
    
    def append_token(self, token: str) -> None:
        """Добавление токена при стриминге"""
        if self.is_streaming:
            self.text += token
    
    def finalize(self) -> None:
        """Завершение стриминга"""
        self.is_streaming = False