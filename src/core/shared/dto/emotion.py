from dataclasses import dataclass


@dataclass
class EmotionDTO:
    """DTO для эмоции."""
    type: str
    intensity: float
    valence: str  # "positive", "negative", "neutral"
    label: str