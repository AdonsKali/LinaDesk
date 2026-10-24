import math
from dataclasses import replace
from datetime import datetime, timezone
from src.core.domain.value_objects.behavior_policy import BehaviorPolicy
from src.core.application.ports.event_port import EventBusPort
from src.core.application.ports.repositories import LinaMemoryRepositoryPort
from src.core.application.subsystems.memory.context import (
    MemoryContext,
    RecalledContext,
)
from src.core.domain.entities.lina import Lina
from src.core.domain.entities.message import Message
from src.core.domain.entities.session import Session
from src.core.domain.events.memory_events import (
    MemoryForgotten,
    MemoryRecalled,
    MemoryStored,
)
from src.core.domain.value_objects.emotion import Valence
from src.core.domain.value_objects.memory_fragment import (
    MemoryFragment,
    MemorySource,
    MemoryZone,
)
from src.core.utils.logger import logger
logger = logger.get(__name__)


class MemoryEngine:
    """
    Логика memory-подсистемы.
    """

    def __init__(
        self,
        memory_repo: LinaMemoryRepositoryPort,
        event_bus: EventBusPort,
        policy: BehaviorPolicy = None,
    ):
        self._repo = memory_repo
        self._bus = event_bus
        self.policy = policy or BehaviorPolicy()

    # =========================================================
    # RECALL (не требует LLM)
    # =========================================================

    async def recall(self, query: str, lina: Lina, user_id=None) -> RecalledContext:
        """Ищет релевантные фрагменты по всем зонам."""
        found = await self._repo.search_many(query, {
            MemoryZone.USER_FACTS: 5, MemoryZone.WORLD_KNOWLEDGE: 3,
            MemoryZone.IDENTITY_FACTS: 3, MemoryZone.DIALOGUE: 5,
        }, user_id=user_id)
        user_facts, world, identity, dialogue = (found[zone] for zone in (
            MemoryZone.USER_FACTS, MemoryZone.WORLD_KNOWLEDGE,
            MemoryZone.IDENTITY_FACTS, MemoryZone.DIALOGUE))
        impactful = lina.memory.mental_impact(limit=self.policy.max_memories)
        if user_id is not None:
            def visible(items):
                return [f for f in items if f.metadata.get("user_id") in (None, str(user_id))]
            user_facts, world, identity, dialogue, impactful = (
                visible(items) for items in (user_facts, world, identity, dialogue, impactful)
            )
        impactful = impactful[:5]

        await self._bus.publish(MemoryRecalled(
            lina_id=lina.id,
            query=query,
            fragments=user_facts + world + identity + dialogue,
        ))

        return RecalledContext(
            user_facts=user_facts,
            world_knowledge=world,
            identity_facts=identity,
            dialogue_summaries=dialogue,
            impactful=impactful,
        )

    # =========================================================
    # APPLY EXTRACTION (после LLM)
    # =========================================================

    async def apply_extraction(
        self,
        raw_fragments: list[dict],
        lina: Lina,
        user_id=None,
        message_id=None,
        evidence_text: str = "",
    ) -> list[MemoryFragment]:
        """Применяет результаты экстракции от LLM к памяти Лины."""
        fragments: list[MemoryFragment] = []

        for item in raw_fragments[:20]:
            if not isinstance(item, dict):
                continue
            if len(fragments) >= self.policy.max_fragments_per_turn:
                break
            if item.get("operation") == "reconsider":
                await self.reconsider_episode(item, lina, user_id, message_id, evidence_text)
                continue
            fragment = self._build_fragment(item, user_id, message_id, evidence_text)
            if fragment is None:
                continue
            if any(f.content.casefold() == fragment.content.casefold()
                   and f.metadata.get("user_id") == fragment.metadata.get("user_id")
                   for f in lina.memory.by_zone(fragment.zone)):
                continue
            lina.memory.remember(fragment)
            await self._repo.upsert_fragment(fragment)
            await self._bus.publish(MemoryStored(
                lina_id=lina.id,
                fragment=fragment,
                zone=fragment.zone,
            ))
            fragments.append(fragment)

        await self.enforce_capacity(lina)
        return fragments

    async def reconsider_episode(self, item, lina, user_id, message_id, observation):
        """Append an interpretation; never rewrite the original event or emotion."""
        confidence = self._number(item.get("confidence"))
        evidence = item.get("evidence")
        interpretation = item.get("interpretation")
        weight = self._number(item.get("relationship_weight"))
        if (confidence is None or confidence < self.policy.min_confidence or weight is None
                or not isinstance(evidence, str) or not evidence.strip()
                or evidence.casefold() not in observation.casefold()
                or not isinstance(interpretation, str) or not interpretation.strip()
                or len(interpretation) > self.policy.max_content_chars):
            return False
        target = next((f for f in lina.memory.all() if str(f.id) == item.get("memory_id")), None)
        if (target is None or "emotional_episode" not in target.tags
                or target.metadata.get("user_id") != str(user_id)
                or target.metadata.get("message_id") == str(message_id)):
            return False
        revisions = list(target.metadata.get("interpretations", []))
        if any(r["message_id"] == str(message_id) for r in revisions):
            return False
        revisions.append({"message_id": str(message_id), "evidence": evidence,
                          "interpretation": interpretation, "confidence": confidence,
                          "relationship_weight": weight,
                          "created_at": datetime.now(timezone.utc).isoformat()})
        updated = replace(target, metadata={**target.metadata, "interpretations": revisions,
                                           "relationship_weight": weight})
        await self._repo.upsert_fragment(updated)
        bucket = lina.memory.fragments[target.zone]
        bucket[bucket.index(target)] = updated
        return True

    def _build_fragment(self, item: dict, user_id, message_id, evidence_text) -> MemoryFragment | None:
        try:
            zone = MemoryZone(item["zone"])
        except (KeyError, ValueError, TypeError):
            return None

        # Model output cannot redefine the configured identity.
        if zone == MemoryZone.IDENTITY_FACTS:
            return None
        content = item.get("content")
        evidence = item.get("evidence")
        importance = self._number(item.get("importance"))
        confidence = self._number(item.get("confidence"))
        if (not isinstance(content, str) or not content.strip()
                or len(content) > self.policy.max_content_chars
                or importance is None or importance < self.policy.min_importance
                or confidence is None or confidence < self.policy.min_confidence
                or not isinstance(evidence, str) or not evidence.strip()
                or evidence.casefold() not in evidence_text.casefold()):
            return None
        fragment = MemoryFragment.create(
            zone=zone,
            content=content.strip(),
            importance=importance,
            source=MemorySource.INFERRED,
            metadata={"user_id": str(user_id), "message_id": str(message_id),
                      "confidence": confidence, "evidence": evidence},
        )
        # Emotional attribution is handled once per turn, by remember_emotion.
        return fragment

    @staticmethod
    def _number(value):
        if isinstance(value, bool):
            return None
        try:
            number = float(value)
            return number if math.isfinite(number) and 0 <= number <= 1 else None
        except (ValueError, TypeError):
            return None

    async def remember_emotion(self, lina, user, message, observation, analysis):
        if not isinstance(analysis, dict):
            return
        confidence = self._number(analysis.get("confidence"))
        evidence = analysis.get("evidence")
        emotion = lina.current_emotion
        if (confidence is None or confidence < self.policy.min_confidence
                or analysis.get("emotion") != emotion.type.value
                or self._number(analysis.get("intensity")) != emotion.intensity
                or emotion.intensity < self.policy.emotional_threshold
                or emotion.valence == Valence.NEUTRAL
                or not isinstance(evidence, str) or not evidence.strip()
                or evidence.casefold() not in observation.casefold()):
            return
        if any(f.metadata.get("message_id") == str(message.id) and "emotional_episode" in f.tags
               for f in lina.memory.all()):
            return
        fragment = MemoryFragment.create(
            zone=MemoryZone.DIALOGUE,
            content=f"Пользователь: «{evidence[:350]}». Моя реакция: {emotion.type.value}.",
            importance=max(self.policy.min_importance, emotion.intensity),
            source=MemorySource.CONVERSATION,
            tags=("emotional_episode",),
            metadata={"user_id": str(user.id), "message_id": str(message.id),
                      "confidence": confidence, "evidence": evidence[:600]},
        ).with_emotion(emotion.valence, emotion.intensity)
        lina.memory.remember(fragment)
        await self._repo.upsert_fragment(fragment)
        await self._bus.publish(MemoryStored(lina_id=lina.id, fragment=fragment, zone=fragment.zone))
        await self.enforce_capacity(lina)

    async def enforce_capacity(self, lina):
        excess = len(lina.memory.all()) - self.policy.max_memories
        for f in sorted(lina.memory.all(), key=lambda f: (f.importance, f.created_at))[:max(0, excess)]:
            lina.memory.forget(f.id)
            await self._repo.delete_fragment(f.id)

    # =========================================================
    # COMPRESSION (после LLM)
    # =========================================================

    def should_compress(self, session: Session) -> bool:
        """Пора ли сжимать сессию?"""
        return (len(session.recent_messages) >= session.max_recent
                or sum(len(m.content) for m in session.recent_messages) > 16000)

    def take_oldest_for_compression(self, session: Session) -> list[Message]:
        """Возвращает старые сообщения для сжатия (не удаляет)."""
        count = max(1, len(session.recent_messages) // 2)
        return session.take_oldest(count)

    async def apply_compression(
        self,
        summary_text: str,
        session: Session,
        lina: Lina,
        dropped_count: int,
    ) -> MemoryFragment | None:
        """Применяет summary от LLM: пишет в память, удаляет старое из сессии."""
        summary_text = summary_text.strip()
        if not summary_text:
            return None

        fragment = MemoryFragment.create(
            zone=MemoryZone.DIALOGUE,
            content=summary_text[:self.policy.max_content_chars],
            importance=0.6,
            source=MemorySource.CONVERSATION,
            metadata={"user_id": str(session.user_id), "session_id": str(session.id)},
        )
        lina.memory.remember(fragment)
        await self._repo.upsert_fragment(fragment)
        session.drop_oldest(dropped_count)
        session.set_context("summary", summary_text[:1500])
        await self.enforce_capacity(lina)

        await self._bus.publish(MemoryForgotten(
            lina_id=lina.id,
            fragment_ids=[],
            reason="compressed_to_summary",
        ))
        return fragment

    # =========================================================
    # DECAY
    # =========================================================

    async def apply_decay(self, lina: Lina) -> None:
        """Затухание важности и эмоций. Вызывается периодически."""
        lina.memory.apply_emotional_decay(factor=0.95)
        lina.memory.apply_importance_decay(factor=0.99)
        for f in lina.memory.all():
            await self._repo.upsert_fragment(f)

    # =========================================================
    # CONTEXT (для отладки)
    # =========================================================

    def build_context(self, lina: Lina) -> MemoryContext:
        all_fragments = lina.memory.all()
        by_zone: dict[str, int] = {}
        for zone in MemoryZone:
            by_zone[zone.value] = len(lina.memory.by_zone(zone))

        return MemoryContext(
            lina_id=lina.id,
            total_fragments=len(all_fragments),
            fragments_by_zone=by_zone,
        )
