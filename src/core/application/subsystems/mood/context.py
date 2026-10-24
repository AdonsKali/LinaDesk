from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from src.core.domain.value_objects.mood import Mood


@dataclass(frozen=True)
class MoodContext:
    """
    Состояние mood-подсистемы.
    """
    current_mood: Mood
    window_days: int = 3
    records_count: int = 0
    positive_score: float = 0.0
    negative_score: float = 0.0
    computed_at: Optional[datetime] = None