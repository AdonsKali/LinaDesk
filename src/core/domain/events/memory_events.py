from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from src.core.domain.events.base import DomainEvent
from src.core.domain.value_objects.memory_fragment import (
    MemoryFragment,
    MemoryZone,
)


@dataclass(kw_only=True)
class MemoryStored(DomainEvent):
    """Фрагмент добавлен в память Лины."""
    lina_id: UUID
    fragment: MemoryFragment
    zone: MemoryZone

    def __post_init__(self):
        self.aggregate_id = str(self.lina_id)


@dataclass(kw_only=True)
class MemoryRecalled(DomainEvent):
    """Из памяти извлечены релевантные фрагменты."""
    lina_id: UUID
    query: str
    fragments: list[MemoryFragment]
    zone: Optional[MemoryZone] = None

    def __post_init__(self):
        self.aggregate_id = str(self.lina_id)


@dataclass(kw_only=True)
class MemoryForgotten(DomainEvent):
    """Фрагменты удалены из памяти."""
    lina_id: UUID
    fragment_ids: list[UUID]
    reason: str = "low_importance"

    def __post_init__(self):
        self.aggregate_id = str(self.lina_id)


@dataclass(kw_only=True)
class SessionMemoryCompressed(DomainEvent):
    """История диалога сжата в summary."""
    session_id: UUID
    summary: MemoryFragment
    dropped_message_count: int

    def __post_init__(self):
        self.aggregate_id = str(self.session_id)