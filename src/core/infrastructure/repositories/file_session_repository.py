import pickle
from pathlib import Path
from typing import Optional
from uuid import UUID

from src.core.application.ports.repositories import SessionRepositoryProt
from src.core.domain.entities.session import Session
from src.core.utils.logger import logger


class FileSessionRepository(SessionRepositoryProt):
    """
    Репозиторий сессии.
    """

    def __init__(self, data_dir: str = "data/sessions"):
        self._dir = Path(data_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._cache: dict[UUID, Session] = {}

    def _path_by_user(self, user_id: UUID) -> Path:
        return self._dir / f"{user_id}.pkl"

    def _path_by_id(self, session_id: UUID) -> Path:
        return self._dir / f"session_{session_id}.pkl"

    async def save(self, session: Session) -> None:
        self._cache[session.id] = session
        with open(self._path_by_user(session.user_id), "wb") as f:
            pickle.dump(session, f)
        with open(self._path_by_id(session.id), "wb") as f:
            pickle.dump(session, f)

    async def get(self, session_id: UUID) -> Optional[Session]:
        if session_id in self._cache:
            return self._cache[session_id]
        path = self._path_by_id(session_id)
        if not path.exists():
            return None
        try:
            with open(path, "rb") as f:
                session = pickle.load(f)
                self._cache[session.id] = session
                return session
        except Exception:
            logger.error(f"Failed to load session {session_id}")
            return None

    async def get_by_user(self, user_id: UUID) -> Optional[Session]:
        for s in self._cache.values():
            if s.user_id == user_id:
                return s
        path = self._path_by_user(user_id)
        if not path.exists():
            return None
        try:
            with open(path, "rb") as f:
                session = pickle.load(f)
                self._cache[session.id] = session
                return session
        except Exception:
            logger.error(f"Failed to load session for user {user_id}")
            return None

    async def ensure_for_user(self, user_id: UUID) -> Session:
        """Гарантирует, что сессия для пользователя существует."""
        existing = await self.get_by_user(user_id)
        if existing:
            return existing
        session = Session.start(user_id)
        await self.save(session)
        return session