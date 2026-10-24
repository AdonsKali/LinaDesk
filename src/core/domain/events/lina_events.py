from dataclasses import dataclass
from uuid import UUID
from src.core.domain.events.base import DomainEvent


@dataclass(kw_only=True)
class NameChanged(DomainEvent):
    """Event: lina's name is changed."""
    old_name: str
    new_name: str
    reason: str
        
        
@dataclass(kw_only=True)
class LinaStatusChanged(DomainEvent):
    status: str
    details: dict