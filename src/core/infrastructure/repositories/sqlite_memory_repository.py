import json
import hashlib
import math
import logging
import re
import sqlite3
from dataclasses import asdict
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from uuid import UUID

from src.core.application.ports.repositories import LinaMemoryRepositoryPort
from src.core.domain.entities.lina_memory import LinaMemory
from src.core.domain.value_objects.memory_fragment import MemoryFragment, MemorySource, MemoryZone
from src.core.domain.value_objects.emotion import Valence


def _encode(fragment):
    data = asdict(fragment)
    for key in ("id", "created_at", "last_accessed_at", "last_emotional_update_at"):
        value = data[key]
        data[key] = value.isoformat() if isinstance(value, datetime) else str(value) if value else None
    return json.dumps(data, ensure_ascii=False)


def _decode(payload):
    data = json.loads(payload)
    data["id"] = UUID(data["id"])
    data["zone"] = MemoryZone(data["zone"])
    data["source"] = MemorySource(data["source"])
    if data["emotional_valence"]:
        data["emotional_valence"] = Valence(data["emotional_valence"])
    for key in ("created_at", "last_accessed_at", "last_emotional_update_at"):
        if data[key]:
            data[key] = datetime.fromisoformat(data[key])
    data["tags"] = tuple(data["tags"])
    return MemoryFragment(**data)


class SQLiteMemoryRepository(LinaMemoryRepositoryPort):
    def __init__(self, path="data/prototype/memory.sqlite3", embeddings=None):
        self._embeddings = embeddings
        self._path = Path(path).resolve()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS memories (id TEXT PRIMARY KEY, zone TEXT NOT NULL, payload TEXT NOT NULL)")
            db.execute("CREATE INDEX IF NOT EXISTS memory_zone ON memories(zone)")
            db.execute("CREATE TABLE IF NOT EXISTS owner (id TEXT PRIMARY KEY)")
            db.execute("CREATE TABLE IF NOT EXISTS vectors (id TEXT PRIMARY KEY, model TEXT NOT NULL, content_hash TEXT NOT NULL, vector TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS core_versions (version INTEGER PRIMARY KEY AUTOINCREMENT, payload TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self._path)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    async def save(self, memory):
        # Snapshot synchronization also persists deletions and decay, atomically.
        with self._connect() as db:
            owner = db.execute("SELECT id FROM owner LIMIT 1").fetchone()
            if owner and owner[0] != str(memory.lina_id):
                raise ValueError("Memory database belongs to another Lina")
            db.execute("INSERT OR IGNORE INTO owner VALUES (?)", (str(memory.lina_id),))
            db.execute("DELETE FROM memories")
            db.executemany("INSERT INTO memories VALUES (?, ?, ?)", [
                (str(f.id), f.zone.value, _encode(f)) for f in memory.all()
            ])
            db.execute("DELETE FROM vectors WHERE id NOT IN (SELECT id FROM memories)")
        await self._index_fragments(memory.all())

    async def record_core(self, policy):
        """Only composition root calls this; learned memories cannot edit core."""
        payload = json.dumps(asdict(policy), ensure_ascii=False, sort_keys=True)
        with self._connect() as db:
            previous = db.execute("SELECT payload FROM core_versions ORDER BY version DESC LIMIT 1").fetchone()
            if previous is None or previous[0] != payload:
                db.execute("INSERT INTO core_versions(payload) VALUES (?)", (payload,))

    async def get_by_lina(self, lina_id):
        with self._connect() as db:
            owner = db.execute("SELECT id FROM owner LIMIT 1").fetchone()
            if owner and owner[0] != str(lina_id):
                raise ValueError("Memory database belongs to another Lina")
            rows = db.execute("SELECT payload FROM memories").fetchall()
        memory = LinaMemory(lina_id=lina_id)
        for row in rows:
            f = _decode(row[0])
            memory.fragments[f.zone].append(f)
        return memory

    async def upsert_fragment(self, fragment):
        with self._connect() as db:
            db.execute("INSERT OR REPLACE INTO memories VALUES (?, ?, ?)",
                       (str(fragment.id), fragment.zone.value, _encode(fragment)))
        await self._index_fragments([fragment])
        logging.getLogger("LinaAI").debug("Memory persisted and indexed: %s", fragment.id)

    async def initialize_index(self):
        """Validate local embeddings and index existing memories before chat starts."""
        logger = logging.getLogger("LinaAI")
        logger.info("Memory database: %s; vector table: vectors", self._path)
        if self._embeddings is None:
            logger.info("Memory search: lexical (no embedding provider configured)")
            return
        logger.info("Embedding model: %s", self._embeddings.model_id)
        probe = self._unit_vector(await self._embeddings.embed_query("Lina memory initialization"))
        with self._connect() as db:
            fragments = [_decode(row[0]) for row in db.execute("SELECT payload FROM memories")]
        vectors = await self._index_fragments(fragments)
        if any(len(vector) != len(probe) for vector in vectors.values()):
            raise ValueError("Memory vector dimensions do not match the embedding model")
        logger.info("Vector memory ready: database=%s, memories=%d, dimensions=%d",
                    self._path, len(fragments), len(probe))

    async def _index_fragments(self, fragments):
        if self._embeddings is None or not fragments:
            return {}
        model = self._embeddings.model_id
        # Read only the relevant rows, rather than every cached vector on each upsert.
        ids = [str(f.id) for f in fragments]
        cached = {}
        with self._connect() as db:
            for start in range(0, len(ids), 500):
                batch = ids[start:start + 500]
                rows = db.execute("SELECT id, model, content_hash, vector FROM vectors WHERE id IN ("
                                  + ",".join("?" for _ in batch) + ")", batch)
                cached.update((row[0], row[1:]) for row in rows)
        missing = []
        vectors = {}
        for fragment in fragments:
            digest = hashlib.sha256(self._search_text(fragment).encode("utf-8")).hexdigest()
            old = cached.get(str(fragment.id))
            if old and old[0] == model and old[1] == digest:
                vectors[str(fragment.id)] = json.loads(old[2])
            else:
                missing.append((fragment, digest))
        for start in range(0, len(missing), 32):
            batch = missing[start:start + 32]
            encoded = await self._embeddings.embed_documents([self._search_text(f) for f, _ in batch])
            if len(encoded) != len(batch):
                raise ValueError("Embedding batch length mismatch")
            with self._connect() as db:
                for (fragment, digest), vector in zip(batch, encoded):
                    vector = self._unit_vector(vector)
                    vectors[str(fragment.id)] = vector
                    db.execute("INSERT OR REPLACE INTO vectors VALUES (?, ?, ?, ?)",
                               (str(fragment.id), model, digest, json.dumps(vector)))
        return vectors

    async def search(self, zone, query, limit=5):
        return (await self.search_many(query, {zone: limit}))[zone]

    async def search_many(self, query, limits, user_id=None):
        """One query vector for all zones, with user isolation BEFORE top-k."""
        result = {zone: [] for zone in limits}
        zones = [zone.value for zone, limit in limits.items() if limit > 0]
        if not zones:
            return result
        sql = "SELECT payload FROM memories WHERE zone IN (" + ",".join("?" for _ in zones) + ")"
        parameters = list(zones)
        if user_id is not None:
            sql += " AND (json_extract(payload, '$.metadata.user_id') IS NULL OR json_extract(payload, '$.metadata.user_id')=?)"
            parameters.append(str(user_id))
        with self._connect() as db:
            fragments = [_decode(row[0]) for row in db.execute(sql, parameters)]
        semantic = {}
        if self._embeddings is not None and fragments:
            vectors = await self._index_fragments(fragments)
            query_vector = self._unit_vector(await self._embeddings.embed_query(query))
            for key, vector in vectors.items():
                if len(vector) != len(query_vector):
                    raise ValueError("Embedding dimensions changed; use a new model_id")
                semantic[key] = sum(a*b for a, b in zip(query_vector, vector))
        words = set(re.findall(r"\w+", query.casefold()))
        def score(f):
            tokens = set(re.findall(r"\w+", f.content.casefold()))
            overlap = len(words & tokens) / max(1, len(words))
            relevance = .8 * semantic[str(f.id)] + .2 * overlap if semantic else overlap
            return (relevance, f.importance, f.created_at)
        for zone, limit in limits.items():
            result[zone] = sorted((f for f in fragments if f.zone == zone),
                                  key=score, reverse=True)[:max(0, limit)]
        logging.getLogger("LinaAI").debug(
            "Memory retrieval: mode=%s candidates=%d selected=%d query_embeddings=%d",
            "semantic+lexical" if semantic else "lexical", len(fragments),
            sum(len(items) for items in result.values()), int(bool(semantic)))
        return result

    async def delete_fragment(self, fragment_id):
        with self._connect() as db:
            db.execute("DELETE FROM memories WHERE id=?", (str(fragment_id),))
            db.execute("DELETE FROM vectors WHERE id=?", (str(fragment_id),))

    @staticmethod
    def _search_text(fragment):
        revisions = fragment.metadata.get("interpretations", [])
        if revisions:
            return fragment.content + "\nПозднейшее объяснение: " + revisions[-1]["interpretation"]
        return fragment.content

    @staticmethod
    def _unit_vector(values):
        vector = [float(x) for x in values]
        if not vector or not all(math.isfinite(x) for x in vector):
            raise ValueError("Invalid embedding vector")
        norm = math.sqrt(sum(x*x for x in vector))
        if norm == 0:
            raise ValueError("Zero embedding vector")
        return [x / norm for x in vector]
