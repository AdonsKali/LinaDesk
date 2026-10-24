from dataclasses import dataclass
from typing import Optional
from uuid import UUID
from src.core.domain.events.base import DomainEvent


@dataclass
class ThoughtGenerated(DomainEvent):
    """
    Event: the agent generated a thought (in autonomous mode).
    """
    thought: str
    confidence: float  # 0.0 – 1.0, how confident the agent is in the thought
    triggered_by: Optional[str] = None  # what sparked the thought
