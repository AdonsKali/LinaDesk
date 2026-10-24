import logging
from datetime import datetime

from src.core.application.ports.event_port import EventBusPort
from src.core.application.subsystems.autonomy.context import AutonomyContext
from src.core.domain.value_objects.autonomy import (
    AutonomyAction,
    Thought,
)
from src.core.domain.events.autonomy_events import (
    AutonomousAction,
    AutonomyChanged,
)

logger = logging.getLogger(__name__)


class AutonomyEngine:
    """
    Логика автономной подсистемы.
    """

    def __init__(self, event_bus: EventBusPort):
        self._bus = event_bus
        self._context = AutonomyContext()

    async def enable(self, reason: str = "user_request") -> None:
        if self._context.is_active:
            return
        self._context = AutonomyContext(is_active=True)
        await self._bus.publish(AutonomyChanged(
            enabled=True,
            request_source=reason,
        ))
        logger.info("[AutonomyEngine] enabled")

    async def disable(self, reason: str = "user_request") -> None:
        if not self._context.is_active:
            return
        self._context = AutonomyContext(is_active=False)
        await self._bus.publish(AutonomyChanged(
            enabled=False,
            request_source=reason,
        ))
        logger.info("[AutonomyEngine] disabled")

    def is_active(self) -> bool:
        return self._context.is_active

    async def apply_thought(
        self,
        raw: dict,
    ) -> tuple[Thought | None, AutonomyAction | None]:
        """
        Применяет результат LLM: строит Thought и AutonomyAction.
        Возвращает (thought, action) или (None, None) при ошибке.
        """
        if not isinstance(raw, dict):
            return None, None
        thought_text = str(raw.get("thought", "")).strip()[:600]
        if not thought_text:
            return None, None

        import math
        try:
            confidence = float(raw.get("confidence", 0))
        except (ValueError, TypeError):
            return None, None
        if not math.isfinite(confidence) or not 0.65 <= confidence <= 1:
            return None, None
        thought = Thought.create(
            content=thought_text,
            confidence=confidence,
            triggered_by="idle",
        )

        action_raw = raw.get("action", {})
        action = self._build_action(action_raw)

        self._context = AutonomyContext(
            is_active=self._context.is_active,
            last_thought=thought,
            last_action=action,
            iterations=self._context.iterations + 1,
            last_tick_at=datetime.now(),
        )

        await self._bus.publish(AutonomousAction(
            action_type=action.type if action else "none",
            description=thought_text,
            result="",
        ))

        return thought, action

    def _build_action(self, raw: dict) -> AutonomyAction | None:
        if not isinstance(raw, dict):
            return None
        t = str(raw.get("type", "none")).lower()
        if t not in ("message", "tool", "none", "move", "animation"):
            t = "none"
        if not isinstance(raw.get("tool_arguments", {}), dict):
            return None
        return AutonomyAction(
            type=t,
            content=str(raw.get("content") or "")[:1000],
            tool_name=raw.get("tool_name"),
            tool_arguments=raw.get("tool_arguments") or {},
        )

    def build_context(self) -> AutonomyContext:
        return self._context
