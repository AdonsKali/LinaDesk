from enum import Enum
from dataclasses import dataclass
from typing import Optional


class MoodType(str, Enum):
    """Type of moods"""
    CHEERFUL = "cheerful"
    ANXIOUS = "anxious"
    CALM = "calm"
    ANNOYED = "annoyed"
    ANGRY = "angry"
    MELANCHOLIC = "melancholic"
    FOCUSED = "focused"


@dataclass(frozen=True)
class Mood:
    type: MoodType
    intensity: float  # 0.0 - 1.0
    description: Optional[str] = None

    def __post_init__(self):
        if not 0.0 <= self.intensity <= 1.0:
            raise ValueError(f"Intensity must be between 0 and 1, got {self.intensity}")

    def is_positive(self) -> bool:
        return self.type in (MoodType.CHEERFUL, MoodType.FOCUSED)

    def is_negative(self) -> bool:
        return self.type in (
            MoodType.ANXIOUS, MoodType.ANNOYED,
            MoodType.ANGRY, MoodType.MELANCHOLIC
        )

    def is_neutral(self) -> bool:
        return self.type == MoodType.CALM

    def is_intense(self, threshold: float = 0.7) -> bool:
        return self.intensity >= threshold

    def shift_towards(self, target_mood: "Mood", factor: float) -> "Mood":
        """
        Плавно смещает настроение в сторону целевого.
        
        factor: скорость смещения от 0.0 до 1.0.
        """
        new_intensity = self.intensity + (target_mood.intensity - self.intensity) * factor
        return Mood(
            type=target_mood.type,
            intensity=new_intensity,
            description=f"Transitioning from {self.type.value}"
        )
        
    def create_by_name(self, name: str) ->  'Mood':
        name = name.lower()
        if name not in MoodType._member_names_:
            raise ValueError(f"Invalid mood name: {name}. Maybe mood is not in types")
        else:
            return Mood(
                type=MoodType[name],
                intensity=self.intensity,
            )

    def create_with_intensity(self, new_intensity: float) -> "Mood":
        """Создает новое настроение с измененной интенсивностью"""
        return Mood(
            type=self.type,
            intensity=new_intensity,
            description=self.description
        )

    def __eq__(self, other) -> bool:
        if not isinstance(other, Mood):
            return False
        return (
            self.type == other.type and
            abs(self.intensity - other.intensity) < 0.01
        )
        
    @classmethod    
    def cheerful(cls) -> 'Mood':
        return cls(
            type=MoodType.CHEERFUL,
            intensity=0.0,
            description="Радостный, настроенный на успех"
        )
        
    @classmethod
    def anxious(cls) -> 'Mood':
        return cls(
            type=MoodType.ANXIOUS,
            intensity=0.0,
            description="Заressed, настроенный на успех"
        )
        
    @classmethod
    def calm(cls) -> 'Mood':
        return cls(
            type=MoodType.CALM,
            intensity=0.0,
            description="Расслабленный, настроенный на успех"
        )
        
    @classmethod
    def annoyed(cls) -> 'Mood':
        return cls(
            type=MoodType.ANNOYED,
            intensity=0.0,
            description="Недоволен, настроенный на успех"
        )
        
    @classmethod
    def angry(cls) -> 'Mood':
        return cls(
            type=MoodType.ANGRY,
            intensity=0.0,
            description="Недоволен, настроенный на успех"
        )
        
    @classmethod
    def melancholic(cls) -> 'Mood':
        return cls(
            type=MoodType.MELANCHOLIC,
            intensity=0.0,
            description="Недоволен, подвален"
        )
        
    @classmethod
    def focused(cls) -> 'Mood':
        return cls(
            type=MoodType.FOCUSED,
            intensity=0.0,
            description="Недоволен, настроенный на успех"
        )