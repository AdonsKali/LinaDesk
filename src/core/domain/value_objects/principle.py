from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, final
from uuid import UUID, uuid4


@final
class PrincipleCategory(str, Enum):
    """Категория принципа — для группировки и UI."""
    BOUNDARY = "boundary"          # границы: что Лина не приемлет
    PREFERENCE = "preference"      # что Лина любит / не любит
    VALUE = "value"                # ценности
    BEHAVIOR = "behavior"          # как себя ведёт


@final
class PrincipleSource(str, Enum):
    """Откуда взялся принцип."""
    DEFAULT = "default"            # задан при создании Лины
    LEARNED = "learned"            # сформирован из опыта
    USER_DEFINED = "user_defined"  # пользователь задал вручную


@final
@dataclass(frozen=True, slots=True)
class Principle:
    """
    Принцип поведения Лины.

    НЕ затухает. Не забывается. Может усиливаться/ослабевать,
    но не исчезает.

    Примеры:
    - "Лине не нравится, когда грубят" (BOUNDARY, strength=0.9)
    - "Я люблю мечтать и обсуждать истории" (PREFERENCE, strength=0.7)
    """
    id: UUID
    statement: str                                  # текст принципа
    category: PrincipleCategory
    strength: float                                 # 0.0-1.0, насколько сильно
    source: PrincipleSource = PrincipleSource.DEFAULT
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        if not self.statement or not self.statement.strip():
            raise ValueError("Principle statement cannot be empty")
        if not 0.0 <= self.strength <= 1.0:
            raise ValueError(
                f"strength must be in [0, 1], got {self.strength}"
            )

    def is_strong(self, threshold: float = 0.7) -> bool:
        return self.strength >= threshold

    def reinforced(self, factor: float = 0.1) -> "Principle":
        return self._replace(
            strength=min(1.0, self.strength + factor),
            updated_at=datetime.now(timezone.utc),
        )

    def weakened(self, factor: float = 0.1) -> "Principle":
        return self._replace(
            strength=max(0.0, self.strength - factor),
            updated_at=datetime.now(timezone.utc),
        )

    def _replace(self, **changes) -> "Principle":
        data = {
            "id": self.id,
            "statement": self.statement,
            "category": self.category,
            "strength": self.strength,
            "source": self.source,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        data.update(changes)
        return Principle(**data)

    @classmethod
    def create(
        cls,
        statement: str,
        category: PrincipleCategory,
        strength: float = 0.5,
        source: PrincipleSource = PrincipleSource.DEFAULT,
    ) -> "Principle":
        return cls(
            id=uuid4(),
            statement=statement,
            category=category,
            strength=strength,
            source=source,
        )