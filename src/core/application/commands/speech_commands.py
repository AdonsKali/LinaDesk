from dataclasses import dataclass
from src.core.application.ports.command_bus import Command


@dataclass
class RecognizeSpeechCommand(Command):
    request_id: str
    pcm: bytes
    sample_rate: int = 16000
