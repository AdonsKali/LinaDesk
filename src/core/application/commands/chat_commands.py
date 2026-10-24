from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional
from src.core.application.ports.command_bus import Command


@dataclass
class SendMessageCommand(Command):
    """Отправка сообщения от пользователя."""
    text: str
    data_files: Optional[List[Dict[str, str]]] = None
    user_id: Optional[str] = None     
    session_id: Optional[str] = None 


@dataclass
class StartVoiceRecordingCommand(Command):
    sample_rate: int = 16000


@dataclass
class StopVoiceRecordingCommand(Command):
    pass