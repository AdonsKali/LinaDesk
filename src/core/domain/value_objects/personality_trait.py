from dataclasses import dataclass
from enum import Enum
from typing import final


@final
class TraitType(str, Enum):
    """Типы черт личности."""
    # Big Five
    OPENNESS = "openness"
    CONSCIENTIOUSNESS = "conscientiousness"
    EXTRAVERSION = "extraversion"
    AGREEABLENESS = "agreeableness"
    NEUROTICISM = "neuroticism"

    # Особые черты LinaAI
    CURIOSITY = "curiosity"
    PLAYFULNESS = "playfulness"
    EMPATHY = "empathy"
    ASSERTIVENESS = "assertiveness"


@final
@dataclass(frozen=True, slots=True)
class PersonalityTrait:
    """Черта личности — значение от 0.0 до 1.0."""
    type: TraitType
    value: float

    def __post_init__(self):
        if not 0.0 <= self.value <= 1.0:
            raise ValueError(
                f"Trait value must be in [0, 1], got {self.value}"
            )

    def is_high(self, threshold: float = 0.7) -> bool:
        return self.value >= threshold

    def is_low(self, threshold: float = 0.3) -> bool:
        return self.value <= threshold

    def scaled(self, factor: float) -> "PersonalityTrait":
        new_value = min(1.0, max(0.0, self.value * factor))
        return PersonalityTrait(type=self.type, value=new_value)