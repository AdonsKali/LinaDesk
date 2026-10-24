from dataclasses import dataclass
from src.core.domain.events.base import DomainEvent


@dataclass
class SpeechRecognized(DomainEvent):
    request_id: str
    text: str


@dataclass
class SpeechRecognitionFailed(DomainEvent):
    request_id: str
    error: str
