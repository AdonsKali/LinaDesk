from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4


@dataclass
class User:
    """
    The base class of user.
    """
    id: UUID
    name: str
    first_seen: datetime
    last_active: datetime
    preferences: dict[str, str]
    preferred_language: str
    interaction_count: int

    def __init__(self, name: str, preferred_language: str = "en"):
        self.id = uuid4()
        self.name = name
        self.preferred_language = preferred_language
        self.first_seen = datetime.now()
        self.last_active = datetime.now()
        self.interaction_count = 0
        self.preferences = {}


    def set_preference(self, key: str, value: str) -> None:
        """Устанавливает предпочтение пользователя"""
        self.preferences[key] = value

    def get_preference(self, key: str, default: str | None = None) -> Optional[str]:
        """Получает предпочтение пользователя"""
        return self.preferences.get(key, default)