from enum import Enum
from datetime import datetime
from typing import Any, Optional, Dict, final
from uuid import UUID, uuid4


@final
class MessageType(str, Enum):
    TEXT = "text"
    VOICE = "voice"
    IMAGE = "image"
    FILE = "file"
    SYSTEM = "system"


@final
class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


@final
class Message:
    """
    The base class of message between user and assistant.
    """
    id: UUID
    role: MessageRole
    type: MessageType
    content: str
    created_at: datetime
    session_id: UUID
    user_id: Optional[UUID]
    metadata: Dict[str, Any]

    def __init__(
        self,
        role: MessageRole,
        content: str,
        session_id: UUID,
        type: MessageType = MessageType.TEXT,
        user_id: Optional[UUID] = None,
        metadata: Optional[dict] = None
    ):
        self.id = uuid4()
        self.role = role
        self.type = type
        self.content = content
        self.session_id = session_id
        self.user_id = user_id
        self.created_at = datetime.now()
        self.metadata = metadata or {}
        
    def __str__(self) -> str:
        return self.content

    def is_from_user(self) -> bool:
        """From user ?"""
        return self.role == MessageRole.USER

    def is_from_assistant(self) -> bool:
        """From assistant ?"""
        return self.role == MessageRole.ASSISTANT