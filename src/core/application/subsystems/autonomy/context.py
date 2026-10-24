from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID

from src.core.domain.value_objects.autonomy import (
    AutonomyAction,
    Thought,
)


@dataclass(frozen=True)
class AutonomyContext:
    """
    Состояние автономной подсистемы.
    """
    is_active: bool = False
    last_thought: Optional[Thought] = None
    last_action: Optional[AutonomyAction] = None
    iterations: int = 0
    last_tick_at: Optional[datetime] = None