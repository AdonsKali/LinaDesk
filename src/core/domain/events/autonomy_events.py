from dataclasses import dataclass
from uuid import UUID
from src.core.domain.events.base import DomainEvent


@dataclass
class AutonomyChanged(DomainEvent):
    """
    Event: autonomy mode changed.
    """
    enabled: bool
    request_source: str


@dataclass
class AutonomousAction(DomainEvent):
    """
    Event: autonomous action taken.
    """
    action_type: str
    description: str
    result: str