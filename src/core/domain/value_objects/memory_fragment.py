# src/core/domain/value_objects/memory_fragment.py
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional, final
from uuid import UUID, uuid4

from src.core.domain.value_objects.emotion import Valence


@final
class MemoryZone(str, Enum):
    """
    Зона памяти = отдельное хранилище (свой FAISS-индекс).

    - IDENTITY_FACTS: что Лина знает о себе
    - USER_FACTS: что Лина знает о пользователе
    - WORLD_KNOWLEDGE: знания из мира (книги, интернет)
    - DIALOGUE: сжатая история диалога
    """
    IDENTITY_FACTS = "identity_facts"
    USER_FACTS = "user_facts"
    WORLD_KNOWLEDGE = "world_knowledge"
    DIALOGUE = "dialogue"


@final
class MemorySource(str, Enum):
    """Откуда пришло воспоминание."""
    CONVERSATION = "conversation"
    USER_STATED = "user_stated"
    INFERRED = "inferred"
    EXTERNAL = "external"
    SYSTEM = "system"


@final
@dataclass(frozen=True, slots=True)
class MemoryFragment:
    """
    Одно воспоминание.

    Эмоциональная окраска опциональна. mental_impact — это view
    в LinaMemory по emotional_intensity >= threshold, не отдельная зона.
    """
    id: UUID
    zone: MemoryZone
    content: str
    importance: float
    created_at: datetime
    source: MemorySource = MemorySource.CONVERSATION

    # Эмоциональная окраска
    emotional_valence: Optional[Valence] = None
    emotional_intensity: float = 0.0
    last_emotional_update_at: Optional[datetime] = None

    # Метрики использования
    last_accessed_at: Optional[datetime] = None
    access_count: int = 0

    # Расширяемость
    tags: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.content or not self.content.strip():
            raise ValueError("MemoryFragment content cannot be empty")
        if not 0.0 <= self.importance <= 1.0:
            raise ValueError(f"importance must be in [0, 1], got {self.importance}")
        if not 0.0 <= self.emotional_intensity <= 1.0:
            raise ValueError(
                f"emotional_intensity must be in [0, 1], got {self.emotional_intensity}"
            )
        if self.emotional_intensity > 0.0 and self.emotional_valence is None:
            raise ValueError("emotional_intensity > 0 requires emotional_valence")
        if self.access_count < 0:
            raise ValueError("access_count cannot be negative")

    def is_important(self, threshold: float = 0.7) -> bool:
        return self.importance >= threshold

    def is_emotionally_significant(self, threshold: float = 0.5) -> bool:
        return self.emotional_intensity >= threshold

    def with_importance(self, new_importance: float) -> "MemoryFragment":
        return replace(self, importance=new_importance)

    def reinforced(self, factor: float = 0.1) -> "MemoryFragment":
        return replace(self, importance=min(1.0, self.importance + factor))

    def decayed_importance(self, factor: float = 0.99) -> "MemoryFragment":
        if not 0.0 < factor <= 1.0:
            raise ValueError("decay factor must be in (0, 1]")
        return replace(self, importance=max(0.0, self.importance * factor))

    def decayed_emotion(
        self,
        factor: float = 0.95,
        now: Optional[datetime] = None,
    ) -> "MemoryFragment":
        if not 0.0 < factor <= 1.0:
            raise ValueError("decay factor must be in (0, 1]")
        return replace(
            self,
            emotional_intensity=max(0.0, self.emotional_intensity * factor),
            last_emotional_update_at=now or datetime.now(timezone.utc),
        )

    def with_emotion(
        self,
        valence: Valence,
        intensity: float,
        now: Optional[datetime] = None,
    ) -> "MemoryFragment":
        return replace(
            self,
            emotional_valence=valence,
            emotional_intensity=intensity,
            last_emotional_update_at=now or datetime.now(timezone.utc),
        )

    def accessed(self, now: Optional[datetime] = None) -> "MemoryFragment":
        return replace(
            self,
            last_accessed_at=now or datetime.now(timezone.utc),
            access_count=self.access_count + 1,
        )

    @classmethod
    def create(
        cls,
        zone: MemoryZone,
        content: str,
        importance: float = 0.5,
        source: MemorySource = MemorySource.CONVERSATION,
        tags: tuple[str, ...] = (),
        metadata: Optional[dict[str, Any]] = None,
    ) -> "MemoryFragment":
        return cls(
            id=uuid4(),
            zone=zone,
            content=content,
            importance=importance,
            created_at=datetime.now(timezone.utc),
            source=source,
            tags=tags,
            metadata=metadata or {},
        )