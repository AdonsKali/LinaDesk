from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from src.core.domain.entities.message import Message


@dataclass
class Session:
    """
    Текущее состояние диалога.
    """
    id: UUID
    user_id: UUID
    started_at: datetime
    last_message_at: Optional[datetime]
    recent_messages: list[Message]
    context: dict[str, Any]
    max_recent: int = 20
    pending_messages: list[Message] = field(default_factory=list, repr=False)

    def __post_init__(self):
        if self.max_recent <= 0:
            raise ValueError("max_recent must be positive")

    @classmethod
    def start(cls, user_id: UUID) -> "Session":
        return cls(
            id=uuid4(),
            user_id=user_id,
            started_at=datetime.now(timezone.utc),
            last_message_at=None,
            recent_messages=[],
            context={},
        )

    # ---------- Сообщения ----------

    def add_message(self, message: Message) -> None:
        """
        Добавляет сообщение в "горячий" кэш.
        НЕ тримит — сжатие делает MemoryEngine, чтобы сначала
        сохранить summary в LinaMemory.
        """
        self.recent_messages.append(message)
        self.pending_messages.append(message)
        self.last_message_at = message.created_at

    def get_recent(self, limit: Optional[int] = None) -> list[Message]:
        """Последние N сообщений (по умолчанию max_recent)."""
        n = limit if limit is not None else self.max_recent
        if n <= 0:
            return []
        return self.recent_messages[-n:]

    def take_oldest(self, count: int) -> list[Message]:
        """
        Возвращает самые старые `count` сообщений.
        """
        if count <= 0:
            return []
        return self.recent_messages[:count]

    def drop_oldest(self, count: int) -> None:
        """Удаляет самые старые `count` сообщений (после сжатия)."""
        if count <= 0:
            return
        self.recent_messages = self.recent_messages[count:]

    def is_full(self) -> bool:
        """
        Готова ли сессия к сжатию.
        """
        return len(self.recent_messages) >= self.max_recent

    def message_count(self) -> int:
        return len(self.recent_messages)

    def clear_messages(self) -> None:
        """Очистить runtime-историю (не память!)."""
        self.recent_messages.clear()

    # ---------- Runtime-контекст ----------

    def set_context(self, key: str, value: Any) -> None:
        self.context[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        return self.context.get(key, default)

    def clear_context(self) -> None:
        self.context.clear()

    def is_empty(self) -> bool:
        return len(self.recent_messages) == 0
