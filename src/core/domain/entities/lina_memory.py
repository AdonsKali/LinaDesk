from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable, Optional
from uuid import UUID

from src.core.domain.value_objects.emotion import Valence
from src.core.domain.value_objects.memory_fragment import (
    MemoryFragment,
    MemorySource,
    MemoryZone,
)


@dataclass
class LinaMemory:
    lina_id: UUID
    fragments: dict[MemoryZone, list[MemoryFragment]] = field(
        default_factory=lambda: {z: [] for z in MemoryZone}
    )
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    # --- Запись ---
    def remember(self, fragment: MemoryFragment) -> None:
        bucket = self.fragments[fragment.zone]
        if self._is_duplicate(bucket, fragment):
            return
        bucket.append(fragment)
        self._touch()

    def remember_many(self, fragments: Iterable[MemoryFragment]) -> None:
        for f in fragments:
            self.remember(f)

    def forget(self, fragment_id: UUID) -> bool:
        for bucket in self.fragments.values():
            for i, f in enumerate(bucket):
                if f.id == fragment_id:
                    bucket.pop(i)
                    self._touch()
                    return True
        return False

    def reinforce(self, fragment_id: UUID, factor: float = 0.1) -> bool:
        for zone, bucket in self.fragments.items():
            for i, f in enumerate(bucket):
                if f.id == fragment_id:
                    self.fragments[zone][i] = f.reinforced(factor)
                    self._touch()
                    return True
        return False

    def add_emotion(
        self,
        fragment_id: UUID,
        valence: Valence,
        intensity: float,
    ) -> bool:
        for zone, bucket in self.fragments.items():
            for i, f in enumerate(bucket):
                if f.id == fragment_id:
                    self.fragments[zone][i] = f.with_emotion(valence, intensity)
                    self._touch()
                    return True
        return False

    # --- Чтение ---
    def by_zone(self, zone: MemoryZone) -> list[MemoryFragment]:
        return list(self.fragments[zone])

    def all(self) -> list[MemoryFragment]:
        return [f for bucket in self.fragments.values() for f in bucket]

    def top_important(
        self, zone: MemoryZone, limit: int = 5
    ) -> list[MemoryFragment]:
        return sorted(
            self.fragments[zone],
            key=lambda f: f.importance,
            reverse=True,
        )[:limit]

    def mental_impact(self, limit: int = 5) -> list[MemoryFragment]:
        """
        Эмоционально значимые воспоминания (view, не зона).
        Сортировка: сначала по интенсивности, потом по свежести.
        """
        impactful = [
            f for f in self.all() if f.is_emotionally_significant()
        ]
        return sorted(
            impactful,
            key=lambda f: (f.emotional_intensity, f.created_at),
            reverse=True,
        )[:limit]

    # --- Политики (вызываются application-сервисом) ---
    def apply_importance_decay(self, factor: float = 0.99) -> None:
        for zone, bucket in self.fragments.items():
            self.fragments[zone] = [f.decayed_importance(factor) for f in bucket]
        self._touch()

    def apply_emotional_decay(self, factor: float = 0.95) -> None:
        for zone, bucket in self.fragments.items():
            self.fragments[zone] = [f.decayed_emotion(factor) for f in bucket]
        self._touch()

    # --- Внутреннее ---
    @staticmethod
    def _is_duplicate(
        bucket: list[MemoryFragment], candidate: MemoryFragment
    ) -> bool:
        normalized = candidate.content.strip().lower()
        return any(
            f.content.strip().lower() == normalized for f in bucket
            if f.metadata.get("user_id") == candidate.metadata.get("user_id")
            and ("emotional_episode" not in candidate.tags
                 or f.metadata.get("message_id") == candidate.metadata.get("message_id"))
        )

    def _touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)

    # --- Удобные фасады (не бизнес-логика, просто конструкторы) ---
    def remember_user_fact(
        self,
        content: str,
        importance: float = 0.7,
        source: MemorySource = MemorySource.USER_STATED,
    ) -> MemoryFragment:
        fragment = MemoryFragment.create(
            zone=MemoryZone.USER_FACTS,
            content=content,
            importance=importance,
            source=source,
        )
        self.remember(fragment)
        return fragment

    def remember_identity_fact(
        self,
        content: str,
        importance: float = 0.6,
    ) -> MemoryFragment:
        fragment = MemoryFragment.create(
            zone=MemoryZone.IDENTITY_FACTS,
            content=content,
            importance=importance,
            source=MemorySource.INFERRED,
        )
        self.remember(fragment)
        return fragment

    def remember_world_knowledge(
        self,
        content: str,
        importance: float = 0.6,
        source: MemorySource = MemorySource.EXTERNAL,
    ) -> MemoryFragment:
        fragment = MemoryFragment.create(
            zone=MemoryZone.WORLD_KNOWLEDGE,
            content=content,
            importance=importance,
            source=source,
        )
        self.remember(fragment)
        return fragment

    def remember_dialogue_summary(
        self,
        content: str,
        importance: float = 0.5,
    ) -> MemoryFragment:
        fragment = MemoryFragment.create(
            zone=MemoryZone.DIALOGUE,
            content=content,
            importance=importance,
            source=MemorySource.CONVERSATION,
        )
        self.remember(fragment)
        return fragment
