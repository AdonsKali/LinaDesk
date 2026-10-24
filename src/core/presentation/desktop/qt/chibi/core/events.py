from dataclasses import dataclass
from typing import Any
from .event_types import EventType

@dataclass
class Event:
    """Событие в системе"""
    type: EventType
    data: Any = None
    source: Any = None