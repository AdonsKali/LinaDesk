from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID

from src.core.domain.value_objects.memory_fragment import MemoryFragment


@dataclass(frozen=True)
class RecalledContext:
    """Результат recall из памяти для текущего запроса."""
    user_facts: list[MemoryFragment] = field(default_factory=list)
    world_knowledge: list[MemoryFragment] = field(default_factory=list)
    identity_facts: list[MemoryFragment] = field(default_factory=list)
    dialogue_summaries: list[MemoryFragment] = field(default_factory=list)
    impactful: list[MemoryFragment] = field(default_factory=list)


@dataclass(frozen=True)
class MemoryContext:
    """Состояние memory-подсистемы (для логов/отладки)."""
    lina_id: UUID
    total_fragments: int = 0
    fragments_by_zone: dict[str, int] = field(default_factory=dict)
    last_updated: Optional[datetime] = None