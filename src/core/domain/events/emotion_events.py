from dataclasses import dataclass
from uuid import UUID
from src.core.domain.events.base import DomainEvent
from src.core.domain.value_objects.emotion import Emotion
from src.core.domain.value_objects.mood import Mood


@dataclass(kw_only=True)
class EmotionChanged(DomainEvent):
    """
    Event: the agent's emotion has changed.
    
    Occurs upon any change in emotional state.
    """
    agent_id: UUID
    old_emotion: Emotion
    new_emotion: Emotion
    reason: str = "unknown"
    intensity_delta: float = 0.0  # изменение интенсивности

    def __post_init__(self):
        self.aggregate_id = str(self.agent_id)
        self.intensity_delta = self.new_emotion.intensity - self.old_emotion.intensity




@dataclass(kw_only=True)
class EmotionIntensified(DomainEvent):
    """
    Event: emotion intensified (type unchanged).
    """
    agent_id: UUID
    emotion: Emotion
    previous_intensity: float
    new_intensity: float
    reason: str = "unknown"

    def __post_init__(self):
        self.aggregate_id = str(self.agent_id)


@dataclass(kw_only=True)
class EmotionWeakened(DomainEvent):
    """
    Event: emotion weakened (type unchanged).
    """
    emotion: Emotion
    previous_intensity: float
    new_intensity: float
    reason: str = "unknown"
        
        
@dataclass(kw_only=True)
class MoodChanged(DomainEvent):
    """
    Event: agent's mood changed.
    
    Occurs when the mood changes (a slower change).
    """
    old_mood: Mood
    new_mood: Mood
    reason: str = "unknown"