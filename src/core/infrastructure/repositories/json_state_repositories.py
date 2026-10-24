import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from uuid import UUID

from src.core.application.ports.repositories import LinaRepository, SessionRepositoryProt, UserRepositoryPort
from src.core.domain.entities.lina import Lina
from src.core.domain.entities.lina_memory import LinaMemory
from src.core.domain.entities.session import Session
from src.core.domain.entities.message import Message, MessageRole, MessageType
from src.core.domain.entities.user import User
from src.core.domain.value_objects.emotion import Emotion, EmotionType
from src.core.domain.value_objects.mood import Mood, MoodType
from src.core.domain.value_objects.personality_trait import PersonalityTrait, TraitType
from src.core.domain.value_objects.principle import Principle, PrincipleCategory, PrincipleSource


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps({"schema_version": 1, **data}, ensure_ascii=False,
                                    indent=2, default=str), encoding="utf-8")
    temporary.replace(path)


def _read(path):
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.pop("schema_version", None) != 1:
        raise ValueError(f"Unsupported state schema: {path}")
    return data


class JsonLinaRepository(LinaRepository):
    def __init__(self, path):
        self.path = Path(path)

    async def save(self, lina):
        _write(self.path, {
            "id": str(lina.id), "name": lina.name,
            "emotion": {"type": lina.current_emotion.type.value, "intensity": lina.current_emotion.intensity},
            "mood": {"type": lina.current_mood.type.value, "intensity": lina.current_mood.intensity},
            "created_at": lina.created_at.isoformat(),
            "personality": {key.value: trait.value for key, trait in lina.personality.items()},
            "principles": [asdict(p) for p in lina.principles],
        })

    async def get(self):
        data = _read(self.path)
        if data is None:
            return None
        uid = UUID(data["id"])
        # Personality configuration is rebuilt, never learned from stored model text.
        lina = Lina.create_default(LinaMemory(uid), name=data["name"])
        lina.id = uid
        lina.created_at = datetime.fromisoformat(data["created_at"])
        lina.personality = {TraitType(key): PersonalityTrait(TraitType(key), value)
                            for key, value in data.get("personality", {}).items()}
        if "principles" in data:
            lina.principles = [Principle(
                id=UUID(p["id"]), statement=p["statement"], category=PrincipleCategory(p["category"]),
                strength=p["strength"], source=PrincipleSource(p["source"]),
                created_at=datetime.fromisoformat(p["created_at"]),
                updated_at=datetime.fromisoformat(p["updated_at"]) if p["updated_at"] else None,
            ) for p in data["principles"]]
        lina.current_emotion = Emotion.from_type(EmotionType(data["emotion"]["type"]), data["emotion"]["intensity"])
        lina.current_mood = Mood(MoodType(data["mood"]["type"]), data["mood"]["intensity"])
        return lina


class JsonUserRepository(UserRepositoryPort):
    def __init__(self, path):
        self.path = Path(path)

    async def save(self, user):
        _write(self.path, asdict(user))

    async def get(self, user_id):
        user = await self.get_default()
        return user if user and user.id == user_id else None

    async def get_default(self):
        data = _read(self.path)
        if data is None:
            return None
        user = User(data["name"], data["preferred_language"])
        user.id = UUID(data["id"])
        user.first_seen = datetime.fromisoformat(data["first_seen"])
        user.last_active = datetime.fromisoformat(data["last_active"])
        user.preferences = data["preferences"]
        user.interaction_count = data["interaction_count"]
        return user


class JsonSessionRepository(SessionRepositoryProt):
    def __init__(self, directory):
        self.directory = Path(directory)

    async def save(self, session):
        messages = [dict(vars(m), role=m.role.value, type=m.type.value) for m in session.recent_messages]
        _write(self.directory / f"{session.user_id}.json", {
            "id": session.id, "user_id": session.user_id, "started_at": session.started_at,
            "last_message_at": session.last_message_at, "messages": messages,
            "context": session.context, "max_recent": session.max_recent,
        })
        session.pending_messages.clear()

    def _decode(self, data):
        session = Session(
            id=UUID(data["id"]), user_id=UUID(data["user_id"]),
            started_at=datetime.fromisoformat(data["started_at"]),
            last_message_at=datetime.fromisoformat(data["last_message_at"]) if data["last_message_at"] else None,
            recent_messages=[], context=data["context"], max_recent=data["max_recent"])
        for item in data["messages"]:
            message = Message(role=MessageRole(item["role"]), content=item["content"],
                              session_id=session.id, type=MessageType(item["type"]),
                              user_id=UUID(item["user_id"]) if item["user_id"] else None,
                              metadata=item["metadata"])
            message.id = UUID(item["id"])
            message.created_at = datetime.fromisoformat(item["created_at"])
            session.recent_messages.append(message)
        return session

    async def get(self, session_id):
        for path in self.directory.glob("*.json"):
            data = _read(path)
            if data["id"] == str(session_id):
                return self._decode(data)
        return None

    async def get_by_user(self, user_id):
        data = _read(self.directory / f"{user_id}.json")
        return self._decode(data) if data else None

    async def ensure_for_user(self, user_id):
        session = await self.get_by_user(user_id)
        if session is None:
            session = Session.start(user_id)
            await self.save(session)
        return session
