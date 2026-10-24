from dataclasses import dataclass
from src.core.domain.events.base import DomainEvent


@dataclass
class SessionStarted(DomainEvent):
    """
    Event: a new session has started.
    """
    session_id: str
    user_id: str


@dataclass
class SessionEnded(DomainEvent):
    """
    Event: session ended.
    """
    session_id: str
    duration_seconds: float
    message_count: int