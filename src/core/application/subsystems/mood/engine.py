from datetime import datetime, timezone
from src.core.application.ports.event_port import EventBusPort
from src.core.application.ports.repositories import EmotionHistoryRepositoryPort
from src.core.application.subsystems.mood.context import MoodContext
from src.core.domain.entities.lina import Lina
from src.core.domain.events.emotion_events import MoodChanged
from src.core.domain.value_objects.emotion import EmotionRecord
from src.core.domain.value_objects.mood import Mood, MoodType

from src.core.utils.logger import logger
logger = logger.get(__name__)


class MoodEngine:
    """
    Логика mood-подсистемы.
    """

    def __init__(
        self,
        history: EmotionHistoryRepositoryPort,
        event_bus: EventBusPort,
        window_days: int = 3,
        threshold: float = 0.3,
    ):
        self._history = history
        self._bus = event_bus
        self._window_days = window_days
        self._threshold = threshold

    # =========================================================
    # PUBLIC
    # =========================================================

    async def update_mood(self, lina: Lina) -> Mood:
        """Пересчитывает mood Лины на основе истории эмоций."""
        records = await self._history.get_last_days(
            lina_id=lina.id,
            days=self._window_days,
        )

        new_mood, positive, negative = self._compute_mood(records)
        old_mood = lina.current_mood

        if old_mood == new_mood:
            logger.debug(
                f"[MoodEngine] mood unchanged: {new_mood.type.value} "
                f"(records={len(records)})"
            )
            return old_mood

        lina.set_mood(new_mood, reason="emotion_history_recalc")
        await self._bus.publish(MoodChanged(
            old_mood=old_mood,
            new_mood=new_mood,
            reason="emotion_history_recalc",
        ))

        logger.info(
            f"[MoodEngine] {old_mood.type.value}({old_mood.intensity:.2f}) → "
            f"{new_mood.type.value}({new_mood.intensity:.2f}) "
            f"[records={len(records)}]"
        )
        return new_mood

    # =========================================================
    # LOGIC
    # =========================================================

    def _compute_mood(
        self,
        records: list[EmotionRecord],
    ) -> tuple[Mood, float, float]:
        """
        Считает mood по записям эмоций.
        Возвращает (mood, positive_score, negative_score).
        """
        if not records:
            return Mood(type=MoodType.CALM, intensity=0.5), 0.0, 0.0

        positive = 0.0
        negative = 0.0
        for r in records:
            e = r.emotion
            if e.is_positive():
                positive += e.intensity
            elif e.is_negative():
                negative += e.intensity

        total = len(records)
        score = (positive - negative) / total   # -1 .. 1

        if score > self._threshold:
            mood = Mood(
                type=MoodType.CHEERFUL,
                intensity=min(1.0, score),
                description=f"Положительный настрой (score={score:.2f})",
            )
        elif score < -self._threshold:
            mood = Mood(
                type=MoodType.ANXIOUS,
                intensity=min(1.0, abs(score)),
                description=f"Негативный настрой (score={score:.2f})",
            )
        else:
            mood = Mood(
                type=MoodType.CALM,
                intensity=0.5,
                description=f"Нейтральный настрой (score={score:.2f})",
            )

        return mood, positive, negative

    # =========================================================
    # CONTEXT (для отладки/UI)
    # =========================================================

    async def build_context(self, lina: Lina) -> MoodContext:
        records = await self._history.get_last_days(
            lina_id=lina.id,
            days=self._window_days,
        )
        _, positive, negative = self._compute_mood(records)

        return MoodContext(
            current_mood=lina.current_mood,
            window_days=self._window_days,
            records_count=len(records),
            positive_score=positive,
            negative_score=negative,
            computed_at=datetime.now(timezone.utc),
        )