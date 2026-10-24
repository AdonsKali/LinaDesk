from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from src.core.domain.value_objects.emotion import Emotion


@dataclass(frozen=True)
class EmotionContext:
    """
    Состояние эмоциональной подсистемы.
    """
    current_emotion: Emotion
    history_size: int = 0
    last_updated: Optional[datetime] = None