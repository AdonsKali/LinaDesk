from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4


@dataclass(kw_only=True, slots=True)
class DomainEvent:
    """
    Base class for all domain events.
    
    Each event has:
    - id: unique event identifier
    - occurred_at: time of occurrence
    - aggregate_id: ID of the entity associated with the event
    - metadata: additional data (optional)
    """
    id: str = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=datetime.now)
    aggregate_id: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def event_type(self) -> str:
        """Returns the event type (class name)."""
        return self.__class__.__name__