from dataclasses import dataclass
from enum import Enum

class BubblePosition(Enum):
    """Позиция облачка относительно чиби"""
    RIGHT_TOP = "right-top"
    LEFT_TOP = "left-top"
    RIGHT_BOTTOM = "right-bottom"
    LEFT_BOTTOM = "left-bottom"

class ChatPosition(Enum):
    """Позиция чата относительно чиби"""
    UNDER = "under"
    ABOVE = "above"

@dataclass
class BubbleModel:
    """Модель облачка с сообщением"""
    is_visible: bool = False
    text: str = ""
    position: BubblePosition = BubblePosition.RIGHT_TOP

@dataclass
class ChatModel:
    """Модель чата"""
    is_visible: bool = False
    is_processing: bool = False
    position: ChatPosition = ChatPosition.UNDER
    input_text: str = ""