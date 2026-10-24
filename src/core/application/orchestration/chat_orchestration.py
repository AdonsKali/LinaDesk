from uuid import UUID
import asyncio
from src.core.application.orchestration.runtime_gate import RuntimeGate

from src.core.application.commands.chat_commands import SendMessageCommand
from src.core.application.orchestration.pipeline import Pipeline
from src.core.application.ports.event_port import EventBusPort
from src.core.application.ports.media_port import MediaProcessorPort
from src.core.application.ports.repositories import (
    LinaMemoryRepositoryPort,
    LinaRepository,
    SessionRepositoryProt,
    UserRepositoryPort,
)
from src.core.domain.entities.message import Message, MessageRole, MessageType
from src.core.domain.domain_error import NotFoundError
from src.core.domain.events.message_events import (
    MessageProcessed,
    MessageReceived,
    ResponseGenerated,
)
from src.core.utils.logger import logger

logger = logger.get(__name__)

_MAX_ATTACHMENTS = 3


class ChatOrchestration:
    def __init__(
        self,
        pipeline: Pipeline,
        users: UserRepositoryPort,
        sessions: SessionRepositoryProt,
        lina_repo: LinaRepository,
        memory_repo: LinaMemoryRepositoryPort,
        media_processor: MediaProcessorPort,
        event_bus: EventBusPort,
        gate: RuntimeGate = None,
    ):
        self._pipeline = pipeline
        self._users = users
        self._sessions = sessions
        self._lina_repo = lina_repo
        self._memory_repo = memory_repo
        self._media = media_processor
        self._bus = event_bus
        self._gate = gate or RuntimeGate()

    async def process_user_message(self, cmd: SendMessageCommand) -> None:
        self._gate.touch()
        async with self._gate.lock:
            if self._gate.stopping:
                raise RuntimeError("Система останавливается.")
            try:
                await self._process(cmd)
            finally:
                self._gate.touch()

    async def _process(self, cmd):
        if len(cmd.text) > 8000:
            raise ValueError("Сообщение слишком длинное (максимум 8000 символов).")
        if len(cmd.data_files or []) > _MAX_ATTACHMENTS:
            raise ValueError("Можно прикрепить не более трёх файлов.")
        logger.info(
            f"[Orchestration] process_user_message "
            f"text={cmd.text[:30]!r} files={len(cmd.data_files or [])}"
        )
        # 1. User
        if cmd.user_id:
            user = await self._users.get(UUID(cmd.user_id))
        else:
            user = await self._users.get_default()
        if user is None:
            raise NotFoundError("User not found")

        # 2. Session
        if cmd.session_id:
            session = await self._sessions.get(UUID(cmd.session_id))
        else:
            session = await self._sessions.get_by_user(user.id)
        if session is None:
            raise NotFoundError("Session not found")
        if session.user_id != user.id:
            raise ValueError("Session does not belong to this user")

        # 3. Lina + memory
        lina = await self._lina_repo.get()
        if lina is None:
            raise NotFoundError("Lina not found")
        memory = await self._memory_repo.get_by_lina(lina.id)
        if memory is None:
            raise NotFoundError("LinaMemory not found")
        lina._memory = memory

        # 4. Media parts
        media_parts = await asyncio.to_thread(self._build_media_parts, cmd.data_files)

        # 5. Message (только text — media передаётся отдельно)
        message = Message(
            role=MessageRole.USER,
            content=cmd.text,
            session_id=session.id,
            user_id=user.id,
            type=MessageType.TEXT,
        )

        await self._bus.publish(MessageReceived(
            message=message,
            session_id=str(session.id),
            user_id=str(user.id),
        ))

        # 6. Pipeline
        response = await self._pipeline.run(
            message, session, lina, user,
            media_parts=media_parts,
        )

        # Persist before announcing successful completion.
        from datetime import datetime
        user.interaction_count += 1
        user.last_active = datetime.now()
        await self._sessions.save(session)
        await self._memory_repo.save(lina.memory)
        await self._lina_repo.save(lina)
        await self._users.save(user)

        # 7. Events
        await self._bus.publish(MessageProcessed(
            original_message_id=message.id,
            response_message=response,
            session_id=session.id,
        ))
        await self._bus.publish(ResponseGenerated(
            message=response,
            session_id=str(session.id),
            agent_id=str(lina.id),
        ))

    def _build_media_parts(self, data_files: list[dict] | None) -> list[dict]:
        """Собирает OpenAI-совместимые parts из data_files."""
        if not data_files:
            return []

        parts: list[dict] = []
        for item in data_files[:_MAX_ATTACHMENTS]:
            path = self._extract_path(item)
            if not path:
                continue
            try:
                if self._media.is_image(path) or self._media.is_audio(path):
                    parts.append(self._media.build_media_part(path))
                elif self._media.is_text(path):
                    text_content = self._media.read_text_file(path)
                    parts.append({
                        "type": "text",
                        "text": f"[File: {path}]\n{text_content}",
                    })
                else:
                    raise ValueError(f"Неподдерживаемый файл: {path}")
            except Exception as exc:
                raise ValueError(f"Не удалось прочитать вложение {path}: {exc}") from exc
        return parts

    @staticmethod
    def _extract_path(item: dict) -> str | None:
        """Извлекает путь из data_files[i]. Поддерживает {'path': ...} и {path: ...}."""
        if not isinstance(item, dict):
            return None
        if "path" in item:
            return item["path"]
        # fallback: первый ключ
        for k in item:
            return k
        return None
