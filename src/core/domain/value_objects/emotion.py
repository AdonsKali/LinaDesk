from datetime import datetime, timezone
from enum import Enum
from dataclasses import dataclass, field
from typing import final
from uuid import UUID, uuid4

@final
class EmotionType(str, Enum):
    """Emotion types"""
    JOY = "joy"
    SADNESS = "sadness"
    ANGER = "anger"
    FEAR = "fear"
    SURPRISE = "surprise"
    DISGUST = "disgust"
    NEUTRAL = "neutral"
    EXCITED = "excited"
    CURIOUS = "curious"
    TIRED = "tired"
    HAPPY = "happy"
    THOUGHTFUL = "thoughtful"

@final
class Valence(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    
    
_VALENCE_BY_TYPE: dict[EmotionType, Valence] = {
    EmotionType.JOY: Valence.POSITIVE,
    EmotionType.SADNESS: Valence.NEGATIVE,
    EmotionType.ANGER: Valence.NEGATIVE,
    EmotionType.FEAR: Valence.NEGATIVE,
    EmotionType.SURPRISE: Valence.POSITIVE,
    EmotionType.DISGUST: Valence.NEGATIVE,
    EmotionType.NEUTRAL: Valence.NEUTRAL,
    EmotionType.EXCITED: Valence.POSITIVE,
    EmotionType.CURIOUS: Valence.NEUTRAL,
    EmotionType.TIRED: Valence.NEGATIVE,
    EmotionType.HAPPY: Valence.POSITIVE,
    EmotionType.THOUGHTFUL: Valence.NEUTRAL,
}
    
    

@final
@dataclass(frozen=True, slots=True)
class Emotion:
    """
    The base value object for emotion.
    """
    type: EmotionType
    intensity: float  # 0.0 - 1.0
    valence: Valence
    label: str 
    
    @classmethod
    def from_type(
        cls,
        etype: EmotionType,
        intensity: float = 0.5,
        label: str | None = None,
    ) -> "Emotion":
        """Создаёт эмоцию с valence, определённым по типу."""
        return cls(
            type=etype,
            intensity=intensity,
            valence=_VALENCE_BY_TYPE.get(etype, Valence.NEUTRAL),
            label=label or etype.value.capitalize(),
        )

    def __post_init__(self):
        if not 0.0 <= self.intensity <= 1.0:
            raise ValueError(f"Intensity must be between 0 and 1, got {self.intensity}")

    def is_positive(self) -> bool:
        return self.valence == Valence.POSITIVE

    def is_negative(self) -> bool:
        return self.valence == Valence.NEGATIVE

    def is_neutral(self) -> bool:
        return self.valence == Valence.NEUTRAL

    def is_intense(self, threshold: float = 0.7) -> bool:
        return self.intensity >= threshold

    def is_weak(self, threshold: float = 0.3) -> bool:
        return self.intensity <= threshold
    
    @staticmethod
    def default_valence(etype: EmotionType) -> Valence:
        return _VALENCE_BY_TYPE.get(etype, Valence.NEUTRAL)
    
    def create_with_intensity(self, new_intensity: float) -> "Emotion":
        """Create a new emotion with a different intensity"""
        return Emotion(
            type=self.type,
            intensity=new_intensity,
            valence=self.valence,
            label=self.label
        )
        
    @staticmethod    
    def create_by_name(name: str, label: str) ->  'Emotion':
        name = name.lower()
        if name not in EmotionType._member_names_:
            raise ValueError(f"Invalid emotion name: {name}. Maybe emotion is not in types")
        else:
            return Emotion(
                type=EmotionType[name],
                intensity=0.0,
                valence=Valence.NEUTRAL,
                label=label
            )

    def create_with_label(self, new_label: str) -> 'Emotion':
        """Create a new emotion with a different label"""
        return Emotion(
            type=self.type,
            intensity=self.intensity,
            valence=self.valence,
            label=new_label
        )

    def __eq__(self, other) -> bool:
        if not isinstance(other, Emotion):
            return False
        return (
            self.type == other.type and
            abs(self.intensity - other.intensity) < 0.01 and
            self.valence == other.valence
        )
        
    @classmethod
    def neutral(cls) -> 'Emotion':
        return cls(
            type=EmotionType.NEUTRAL,
            intensity=0.0,
            valence=Valence.NEUTRAL,
            label="Neutral"
        )
        
    @classmethod
    def joy(cls) -> 'Emotion':
        return cls(
            type=EmotionType.JOY,
            intensity=0.0,
            valence=Valence.POSITIVE,
            label="Joy"
        )
        
    @classmethod
    def sadness(cls) -> 'Emotion':
        return cls(
            type=EmotionType.SADNESS,
            intensity=0.0,
            valence=Valence.NEGATIVE,
            label="Sadness"
        )
        
    @classmethod
    def anger(cls) -> 'Emotion':
        return cls(
            type=EmotionType.ANGER,
            intensity=0.0,
            valence=Valence.NEGATIVE,
            label="Anger"
        )
        
    @classmethod
    def fear(cls) -> 'Emotion':
        return cls(
            type=EmotionType.FEAR,
            intensity=0.0,
            valence=Valence.NEGATIVE,
            label="Fear"
        )
        
    @classmethod
    def surprise(cls) -> 'Emotion':
        return cls(
            type=EmotionType.SURPRISE,
            intensity=0.0,
            valence=Valence.POSITIVE,
            label="Surprise"
        )
        
        
    @classmethod
    def disgust(cls) -> 'Emotion':
        return cls(
            type=EmotionType.DISGUST,
            intensity=0.0,
            valence=Valence.NEGATIVE,
            label="Disgust"
        )
        
    @classmethod
    def excited(cls) -> 'Emotion':
        return cls(
            type=EmotionType.EXCITED,
            intensity=0.0,
            valence=Valence.POSITIVE,
            label="Excited"
        )
        
    @classmethod
    def curious(cls) -> 'Emotion':
        return cls(
            type=EmotionType.CURIOUS,
            intensity=0.0,
            valence=Valence.NEUTRAL,
            label="Curious"
        )
        
    @classmethod
    def tired(cls) -> 'Emotion':
        return cls(
            type=EmotionType.TIRED,
            intensity=0.0,
            valence=Valence.NEGATIVE,
            label="Tired"
        )
        
    @classmethod
    def happy(cls) -> 'Emotion':
        return cls(
            type=EmotionType.HAPPY,
            intensity=0.0,
            valence=Valence.POSITIVE,
            label="Happy"
        )
        
    @classmethod
    def thoughtful(cls) -> 'Emotion':
        return cls(
            type=EmotionType.THOUGHTFUL,
            intensity=0.0,
            valence=Valence.NEUTRAL,
            label="Thoughtful"
        )

@final
@dataclass(frozen=True, slots=True)
class EmotionRecord:
    id: UUID
    emotion: Emotion
    recorded_at: datetime
    trigger: str = ""
    trigger_text: str = ""
    metadata: dict = field(default_factory=dict)

    @classmethod
    def create(cls, emotion, trigger="", trigger_text="", metadata=None) -> "EmotionRecord":
        return cls(
            id=uuid4(),
            emotion=emotion,
            recorded_at=datetime.now(timezone.utc),
            trigger=trigger,
            trigger_text=trigger_text,
            metadata=metadata or {},
        )