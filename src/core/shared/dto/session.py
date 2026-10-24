from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class SessionDTO:
    """DTO для сессии."""
    id: str
    user_id: str
    agent_id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    is_active: bool = True
    message_count: int = 0

