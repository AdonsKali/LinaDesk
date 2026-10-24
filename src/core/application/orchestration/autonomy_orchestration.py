import asyncio
import logging
import time
import random
from src.core.domain.value_objects.behavior_policy import BehaviorPolicy
from src.core.application.orchestration.runtime_gate import RuntimeGate
from src.core.domain.events.desktop_events import DesktopActionRequested

from src.core.application.orchestration.prompting.builder import PromptBuilder
from src.core.application.ports.event_port import EventBusPort
from src.core.application.ports.llm_port import LLMPort
from src.core.application.subsystems.autonomy.engine import AutonomyEngine
from src.core.application.subsystems.autonomy.prompts import build_thought_prompt
from src.core.application.subsystems.emotion.engine import EmotionEngine
from src.core.application.subsystems.memory.engine import MemoryEngine
from src.core.application.subsystems.mood.engine import MoodEngine
from src.core.application.subsystems.tools.engine import ToolEngine
from src.core.domain.entities.lina import Lina
from src.core.domain.entities.session import Session
from src.core.domain.entities.user import User
from src.core.domain.events.message_events import ResponseGenerated

logger = logging.getLogger(__name__)


class AutonomyOrchestration:
    """
    Цикл автономного поведения.
    """

    def __init__(
        self,
        autonomy: AutonomyEngine,
        memory: MemoryEngine,
        emotion: EmotionEngine,
        mood: MoodEngine,
        tools: ToolEngine,
        llm: LLMPort,
        prompts: PromptBuilder,
        event_bus: EventBusPort,
        tick_interval_seconds: float = 20.0,
        gate=None,
        policy=None,
        lina_repo=None,
        users=None,
        sessions=None,
        memory_repo=None,
    ):
        self._autonomy = autonomy
        self._memory = memory
        self._emotion = emotion
        self._mood = mood
        self._tools = tools
        self._llm = llm
        self._prompts = prompts
        self._bus = event_bus
        self._tick_interval = tick_interval_seconds
        self._task: asyncio.Task | None = None
        self._gate = gate or RuntimeGate()
        self._policy = policy or BehaviorPolicy()
        self._lina_repo, self._users = lina_repo, users
        self._sessions, self._memory_repo = sessions, memory_repo
        self._last_message = 0.0
        self._recent_actions = []

    async def start(
        self,
        lina: Lina,
        user: User,
        session: Session,
        reason: str = "user_request",
    ) -> None:
        if self._autonomy.is_active():
            return
        await self._autonomy.enable(reason=reason)
        self._task = asyncio.create_task(self._loop(lina, user, session))
        logger.info("[AutonomyOrchestration] started")

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        await self._autonomy.disable()
        logger.info("[AutonomyOrchestration] stopped")

    async def _loop(self, lina: Lina, user: User, session: Session) -> None:
        try:
            while self._autonomy.is_active():
                await asyncio.sleep(self._policy.autonomy_interval_seconds * random.uniform(0.85, 1.15))
                if not self._autonomy.is_active():
                    break
                try:
                    if not self._gate.idle(self._policy.idle_seconds):
                        continue
                    async with self._gate.lock:
                        if self._gate.stopping:
                            break
                        # Repositories are authoritative; don't retain a stale startup snapshot.
                        current_lina = await self._lina_repo.get()
                        current_user = await self._users.get(user.id)
                        current_session = await self._sessions.get(session.id)
                        if not all((current_lina, current_user, current_session)):
                            continue
                        current_lina._memory = await self._memory_repo.get_by_lina(current_lina.id)
                        await self._tick(current_lina, current_user, current_session)
                        await self._sessions.save(current_session)
                        await self._lina_repo.save(current_lina)
                        await self._memory_repo.save(current_lina.memory)
                except Exception:
                    logger.exception("[AutonomyOrchestration] tick failed")
        except asyncio.CancelledError:
            logger.info("[AutonomyOrchestration] loop cancelled")
            raise

    async def _tick(self, lina: Lina, user: User, session: Session) -> None:
        logger.info("[AutonomyOrchestration] tick")

        # 1. Recall памяти (последнее сообщение / контекст)
        last_message = ""
        recent = session.get_recent(limit=1)
        if recent:
            last_message = recent[-1].content

        recalled = await self._memory.recall(last_message, lina, user.id)
        allowed_tools = [t for t in await self._tools.get_available_tools()
                         if t.name in self._policy.autonomous_tools]

        # 2. Собрать секции через PromptBuilder
        sections = self._prompts.build_sections(
            lina=lina,
            user=user,
            recalled=recalled,
            tools=allowed_tools,
        )
        sections.append("Recent conversation (data):\n" + "\n".join(
            f"{m.role.value}: {m.content[:600]}" for m in session.get_recent(4)))
        sections.append("Recent autonomous actions: " + repr(self._recent_actions))

        # 3. Построить промпт с инструкцией мысли
        prompt = build_thought_prompt(sections)

        # 4. LLM
        try:
            raw = await self._llm.infer_json(prompt)
        except Exception:
            logger.exception("[AutonomyOrchestration] LLM failed")
            return

        # 5. Применить
        thought, action = await self._autonomy.apply_thought(raw)
        if thought is None:
            return

        logger.info(
            f"[AutonomyOrchestration] thought: {thought.content!r} "
            f"(confidence={thought.confidence:.2f}, "
            f"action={action.type if action else 'none'})"
        )

        # 6. Действие
        if action is None or action.type == "none":
            return
        # If a user arrived during inference, discard this idea.
        if self._gate.stopping or time.monotonic() - self._gate.last_user_activity < self._policy.idle_seconds:
            return
        signature = (action.type, action.content, action.tool_name)
        if signature in self._recent_actions:
            return
        self._recent_actions = (self._recent_actions + [signature])[-5:]

        if action.type == "message":
            if time.monotonic() - self._last_message >= self._policy.message_cooldown_seconds:
                await self._handle_message_action(action, session, lina)
                self._last_message = time.monotonic()

        elif action.type == "tool":
            await self._handle_tool_action(action, user)
        elif action.type == "move":
            if action.content in ("left", "right", "random"):
                await self._bus.publish(DesktopActionRequested(action="move", value=action.content))
        elif action.type == "animation":
            if action.content in ("idle", "think", "talk", "process"):
                await self._bus.publish(DesktopActionRequested(action="animation", value=action.content))

    async def _handle_message_action(
        self,
        action,
        session: Session,
        lina: Lina,
    ) -> None:
        """Лина сама пишет пользователю."""
        from src.core.domain.entities.message import (
            Message,
            MessageRole,
            MessageType,
        )
        if not action.content:
            return
        msg = Message(
            role=MessageRole.ASSISTANT,
            content=action.content,
            session_id=session.id,
            type=MessageType.TEXT,
        )
        session.add_message(msg)
        if len(session.recent_messages) > session.max_recent:
            old = session.take_oldest(len(session.recent_messages) - session.max_recent)
            await self._memory.apply_compression(
                "\n".join(m.content[:200] for m in old)[:1200], session, lina, len(old))
            await self._memory.enforce_capacity(lina)
        await self._sessions.save(session)
        await self._bus.publish(ResponseGenerated(
            message=msg,
            session_id=str(session.id),
            agent_id="autonomy",
        ))

    async def _handle_tool_action(self, action, user: User) -> None:
        """Лина вызывает инструмент."""
        if not action.tool_name or action.tool_name not in self._policy.autonomous_tools:
            return
        from src.core.domain.value_objects.tool import ToolCall
        call = ToolCall(
            name=action.tool_name,
            arguments=action.tool_arguments,
        )
        result = await self._tools.execute(call, user)
        self._recent_actions.append(("tool_result", result.to_llm_content()[:500], None))
        self._recent_actions = self._recent_actions[-5:]
