from abc import ABC, abstractmethod
from typing import Optional, List, Any
from uuid import UUID

from src.core.domain.value_objects.emotion import EmotionRecord
from src.core.domain.value_objects.plugin import Plugin
from src.core.domain.entities.session import Session
from src.core.domain.entities.lina import Lina
from src.core.domain.entities.lina_memory import LinaMemory
from src.core.domain.entities.user import User
from src.core.domain.value_objects.settings import Settings
from src.core.domain.value_objects.memory_fragment import (
    MemoryFragment,
    MemoryZone,
)


class LinaRepository(ABC):
    """Репозиторий для агента Lina."""

    @abstractmethod
    async def save(self, lina: Lina) -> None: ...

    @abstractmethod
    async def get(self) -> Optional[Lina]: ...
    
    
class EmotionHistoryRepositoryPort(ABC):
    """История эмоций Лины для расчёта настроения."""

    @abstractmethod
    async def add(self, lina_id: UUID, record: EmotionRecord) -> None: ...

    @abstractmethod
    async def get_last_days(
        self,
        lina_id: UUID,
        days: int = 3,
    ) -> list[EmotionRecord]: ...

    @abstractmethod
    async def get_recent(
        self,
        lina_id: UUID,
        limit: int = 20,
    ) -> list[EmotionRecord]: ...

    @abstractmethod
    async def clear(self, lina_id: UUID) -> None: ...


class SessionRepositoryProt(ABC):

    @abstractmethod
    async def save(self, session: Session) -> None: ...

    @abstractmethod
    async def get(self, session_id: UUID) -> Optional[Session]: ...

    @abstractmethod
    async def get_by_user(self, user_id: UUID) -> Optional[Session]: ...

    @abstractmethod
    async def ensure_for_user(self, user_id: UUID) -> Session: ...


class UserRepositoryPort(ABC):
    """Репозиторий пользователя."""

    @abstractmethod
    async def save(self, user: User) -> None: ...

    @abstractmethod
    async def get(self, user_id: UUID) -> Optional[User]: ...

    @abstractmethod
    async def get_default(self) -> Optional[User]: ...


class LinaMemoryRepositoryPort(ABC):
    """
    Репозиторий памяти Лины.
    Векторный поиск — на стороне инфраструктуры (FAISS),
    но репозиторий даёт единый интерфейс.
    """

    @abstractmethod
    async def save(self, memory: LinaMemory) -> None: ...

    @abstractmethod
    async def get_by_lina(self, lina_id: UUID) -> Optional[LinaMemory]: ...

    @abstractmethod
    async def upsert_fragment(self, fragment: MemoryFragment) -> None: ...

    @abstractmethod
    async def search(
        self,
        zone: MemoryZone,
        query: str,
        limit: int = 5,
    ) -> List[MemoryFragment]: ...

    async def search_many(self, query, limits, user_id=None):
        """Portable fallback; implementations can share one query embedding."""
        result = {}
        for zone, limit in limits.items():
            items = await self.search(zone, query, limit=limit)
            result[zone] = [f for f in items if user_id is None or
                            f.metadata.get("user_id") in (None, str(user_id))]
        return result

    @abstractmethod
    async def delete_fragment(self, fragment_id: UUID) -> None: ...


class PluginRepositoryPort(ABC):
    """Репозиторий плагинов."""

    @abstractmethod
    async def get_enabled_plugins(self) -> List[Any]: ...

    @abstractmethod
    async def get_plugin(self, plugin_name: str) -> Optional[Any]: ...

    @abstractmethod
    async def save(self, plugin: Plugin) -> None: ...




class SettingsRepository(ABC):
    """Репозиторий настроек"""
    
    @abstractmethod
    async def get(self) -> Optional[Settings]:
        """Получение настроек"""
        pass
    
    @abstractmethod
    async def save(self, settings: Settings) -> None:
        """Сохранение настроек"""
        pass
