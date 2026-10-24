import json
import sqlite3
from pathlib import Path
from contextlib import contextmanager
from src.core.infrastructure.repositories.json_state_repositories import JsonSessionRepository


class SQLiteSessionRepository(JsonSessionRepository):
    def __init__(self, path, legacy_directory):
        super().__init__(legacy_directory)
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, user_id TEXT NOT NULL, payload TEXT NOT NULL)")
            db.execute("CREATE INDEX IF NOT EXISTS sessions_user ON sessions(user_id)")
            db.execute("CREATE TABLE IF NOT EXISTS messages (id TEXT PRIMARY KEY, session_id TEXT NOT NULL, payload TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS migrations (name TEXT PRIMARY KEY)")
            if not db.execute("SELECT 1 FROM migrations WHERE name='legacy_json'").fetchone():
                for source in self.directory.glob("*.json"):
                    data = json.loads(source.read_text(encoding="utf-8-sig"))
                    self._decode(data)  # Validate before committing the migration.
                    db.execute("INSERT OR IGNORE INTO sessions VALUES (?, ?, ?)",
                               (data["id"], data["user_id"], json.dumps(data, ensure_ascii=False)))
                db.execute("INSERT INTO migrations VALUES ('legacy_json')")
            # Also repair archives created before separate message storage existed.
            if not db.execute("SELECT 1 FROM migrations WHERE name='message_archive'").fetchone():
                for row in db.execute("SELECT id, payload FROM sessions").fetchall():
                    for message in json.loads(row[1])["messages"]:
                        db.execute("INSERT OR IGNORE INTO messages VALUES (?, ?, ?)",
                                   (message["id"], row[0], json.dumps(message, ensure_ascii=False)))
                db.execute("INSERT INTO migrations VALUES ('message_archive')")

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path)
        try:
            with db:
                yield db
        finally:
            db.close()

    async def save(self, session):
        data = {
            "id": session.id, "user_id": session.user_id, "started_at": session.started_at,
            "last_message_at": session.last_message_at, "context": session.context,
            "max_recent": session.max_recent,
            "messages": [dict(vars(m), role=m.role.value, type=m.type.value) for m in session.recent_messages],
        }
        def encode(value):
            return value.isoformat() if hasattr(value, "isoformat") else str(value)
        with self._connect() as db:
            # A compression can remove a just-created message from the hot cache
            # before save. Archive it anyway, and clear pending only after commit.
            archive = {m["id"]: m for m in data["messages"]}
            archive.update((m.id, dict(vars(m), role=m.role.value, type=m.type.value))
                           for m in session.pending_messages)
            for message in archive.values():
                db.execute("INSERT OR REPLACE INTO messages VALUES (?, ?, ?)", (str(message["id"]), str(session.id), json.dumps(message, default=encode, ensure_ascii=False)))
            db.execute("INSERT OR REPLACE INTO sessions VALUES (?, ?, ?)",
                       (str(session.id), str(session.user_id), json.dumps(data, default=encode, ensure_ascii=False)))
        session.pending_messages.clear()

    async def get(self, session_id):
        with self._connect() as db:
            row = db.execute("SELECT payload FROM sessions WHERE id=?", (str(session_id),)).fetchone()
        return self._decode(json.loads(row[0])) if row else None

    async def get_by_user(self, user_id):
        with self._connect() as db:
            row = db.execute("SELECT payload FROM sessions WHERE user_id=? ORDER BY json_extract(payload, '$.started_at') DESC LIMIT 1", (str(user_id),)).fetchone()
        return self._decode(json.loads(row[0])) if row else None

    async def get_messages(self, session_id, limit=100, offset=0):
        """Read chronological archived messages independently of hot context."""
        with self._connect() as db:
            rows = db.execute(
                "SELECT payload FROM messages WHERE session_id=? ORDER BY json_extract(payload, '$.created_at'), id LIMIT ? OFFSET ?",
                (str(session_id), max(0, min(limit, 1000)), max(0, offset))).fetchall()
        return [json.loads(row[0]) for row in rows]
