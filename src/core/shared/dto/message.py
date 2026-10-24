from dataclasses import dataclass
from typing import Optional, Any
from datetime import datetime


@dataclass
class MessageDTO:
    """
    DTO для сообщения.
    """
    id: str
    role: str  # "user", "agent", "system"
    content: str
    session_id: str
    user_id: Optional[str] = None
    agent_id: Optional[str] = None
    created_at: Optional[datetime] = None
    metadata: Optional[dict[str, Any]] = None