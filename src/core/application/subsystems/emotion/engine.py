from src.core.application.ports.event_port import EventBusPort
from src.core.application.ports.repositories import EmotionHistoryRepositoryPort
from src.core.application.subsystems.emotion.context import EmotionContext
from src.core.domain.entities.lina import Lina
from src.core.domain.events.emotion_events import EmotionChanged
from src.core.domain.value_objects.emotion import (
    Emotion,
    EmotionRecord,
    EmotionType,
)
from src.core.utils.logger import logger
logger = logger.get(__name__)


class EmotionEngine:
    """
    Логика эмоциональной подсистемы.
    """

    def __init__(
        self,
        event_bus: EventBusPort,
        history: EmotionHistoryRepositoryPort,
    ):
        self._bus = event_bus
        self._history = history

    async def apply(
        self,
        raw_result: dict,
        lina: Lina,
        user_message: str,
    ) -> Emotion:
        """
        Применяет результат анализа LLM к Лине.
        Возвращает новую эмоцию (или текущую, если парсинг не удался).
        """
        new_emotion = self._build_emotion(raw_result)

        if new_emotion is None:
            logger.warning(
                f"[EmotionEngine] could not parse emotion from {raw_result!r}"
            )
            return lina.current_emotion

        old = lina.current_emotion
        lina.set_emotion(new_emotion, reason="response_to_user")

        logger.info(
            f"[EmotionEngine] {old.type.value}({old.intensity}) → "
            f"{new_emotion.type.value}({new_emotion.intensity})"
        )

        # Записываем в историю
        record = EmotionRecord.create(
            emotion=new_emotion,
            trigger="user_message",
            trigger_text=user_message[:200],
        )
        await self._history.add(lina.id, record)

        await self._bus.publish(EmotionChanged(
            agent_id=lina.id,
            old_emotion=old,
            new_emotion=new_emotion,
            reason="response_to_user",
        ))

        return new_emotion

    def build_context(self, lina: Lina, history_size: int = 0) -> EmotionContext:
        """Собирает контекст подсистемы."""
        from datetime import datetime, timezone
        return EmotionContext(
            current_emotion=lina.current_emotion,
            history_size=history_size,
            last_updated=datetime.now(timezone.utc),
        )

    def _build_emotion(self, data: dict) -> Emotion | None:
        if not isinstance(data, dict):
            return None

        name = str(data.get("emotion", "")).strip().lower()
        if not name:
            return None

        try:
            etype = EmotionType(name)
        except ValueError:
            return None

        import math
        try:
            intensity = float(data.get("intensity", 0.5))
        except (ValueError, TypeError):
            return None
        if not math.isfinite(intensity) or not 0 <= intensity <= 1:
            return None
        
        return Emotion.from_type(etype, intensity=intensity)
