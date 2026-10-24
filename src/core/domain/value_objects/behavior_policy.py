from dataclasses import dataclass
import math


@dataclass(frozen=True)
class BehaviorPolicy:
    identity: tuple[str, ...] = (
        "Я Лина, любознательный настольный персонаж.",
        "Я боюсь пауков",
        "Я ценю доброжелательность и совместное общение.",
        "Я начинаю злиться если пользователь начинает обижать меня "
    )
    min_importance: float = 0.65
    min_confidence: float = 0.8
    emotional_threshold: float = 0.55
    max_fragments_per_turn: int = 3
    max_memories: int = 2000
    max_content_chars: int = 600
    relationship_step: float = 0.08
    relationship_half_life_days: float = 30.0
    autonomy_interval_seconds: float = 60.0
    idle_seconds: float = 45.0
    message_cooldown_seconds: float = 300.0
    autonomous_tools: tuple[str, ...] = ("execute_command")

    def __post_init__(self):
        for key in ("min_importance", "min_confidence", "emotional_threshold",
                    "relationship_step"):
            value = getattr(self, key)
            if not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f"{key} must be in [0, 1]")
        for key in ("max_fragments_per_turn", "max_memories", "max_content_chars"):
            if type(getattr(self, key)) is not int or getattr(self, key) < 1:
                raise ValueError(f"{key} must be a positive integer")
        for key in ("relationship_half_life_days", "autonomy_interval_seconds",
                    "idle_seconds", "message_cooldown_seconds"):
            value = getattr(self, key)
            if not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"{key} must be positive")
        if not self.identity or any(not isinstance(x, str) or not x.strip() for x in self.identity):
            raise ValueError("identity must contain nonempty strings")
        if any(not isinstance(x, str) for x in self.autonomous_tools):
            raise ValueError("autonomous_tools must contain tool names")

    @classmethod
    def from_dict(cls, data):
        values = dict(data)
        for key in ("identity", "autonomous_tools"):
            if key in values:
                if not isinstance(values[key], list):
                    raise ValueError(f"{key} must be an array")
                values[key] = tuple(values[key])
        return cls(**values)
