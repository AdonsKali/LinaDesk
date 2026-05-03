from dataclasses import dataclass, field
from typing import List
from enum import Enum, auto

class MessageSource(Enum):
    """Источник сообщения"""
    USER = auto()
    AI = auto()
    SYSTEM = auto()

@dataclass
class MessageModel:
    """Модель сообщения"""
    text: str = ""
    source: MessageSource = MessageSource.AI
    is_streaming: bool = False
    
    def append_token(self, token: str) -> None:
        """Добавление токена при стриминге"""
        if self.is_streaming:
            self.text += token
    
    def finalize(self) -> None:
        """Завершение стриминга"""
        self.is_streaming = False