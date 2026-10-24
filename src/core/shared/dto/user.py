from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class UserDTO:
    """DTO для пользователя."""
    id: str
    name: str
    preferred_language: str = "en"
    first_seen: Optional[datetime] = None
    last_active: Optional[datetime] = None
    interaction_count: int = 0
    preferences: Optional[dict[str, str]] = None
