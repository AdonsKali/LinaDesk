from uuid import uuid4
from src.core.domain.entities.session import Session
from src.core.domain.value_objects.memory_fragment import MemoryFragment, MemoryZone, MemorySource
from src.core.infrastructure.repositories.sqlite_memory_repository import SQLiteMemoryRepository
from src.core.infrastructure.repositories.sqlite_session_repository import SQLiteSessionRepository
from src.core.infrastructure.repositories.json_state_repositories import JsonSessionRepository


async def test_session_migration_keeps_original(tmp_path):
    legacy = JsonSessionRepository(tmp_path / "sessions")
    session = Session.start(uuid4())
    await legacy.save(session)
    repo = SQLiteSessionRepository(tmp_path / "conversations.sqlite3", legacy.directory)
    assert (await repo.get_by_user(session.user_id)).id == session.id
    assert (legacy.directory / f"{session.user_id}.json").is_file()
    await repo.save(session)
    assert (await repo.get(session.id)).id == session.id


async def test_semantic_search_caches_vectors_and_invalidates_content(tmp_path):
    class Embeddings:
        model_id = "test-v1"
        calls = 0
        async def embed_documents(self, texts):
            self.calls += 1
            return [[1, 0] if text == "spider" else [0, 1] for text in texts]
        async def embed_query(self, text):
            return [1, 0]
    embeddings = Embeddings()
    repo = SQLiteMemoryRepository(tmp_path / "memory.sqlite3", embeddings)
    spider = MemoryFragment.create(zone=MemoryZone.USER_FACTS, content="spider", importance=.8, source=MemorySource.INFERRED)
    other = MemoryFragment.create(zone=MemoryZone.USER_FACTS, content="coffee", importance=.9, source=MemorySource.INFERRED)
    await repo.upsert_fragment(spider)
    await repo.upsert_fragment(other)
    assert (await repo.search(MemoryZone.USER_FACTS, "eight legs", 1))[0].id == spider.id
    indexed_calls = embeddings.calls
    await repo.search(MemoryZone.USER_FACTS, "eight legs", 1)
    assert embeddings.calls == indexed_calls
    await repo.delete_fragment(spider.id)
    assert (await repo.search(MemoryZone.USER_FACTS, "eight legs", 1))[0].id == other.id


async def test_archive_survives_hot_context_compression(tmp_path):
    from src.core.domain.entities.message import Message, MessageRole
    legacy = JsonSessionRepository(tmp_path / "sessions")
    session = Session.start(uuid4())
    message = Message(role=MessageRole.USER, content="remember this", session_id=session.id)
    session.add_message(message)
    await legacy.save(session)
    repo = SQLiteSessionRepository(tmp_path / "conversations.sqlite3", legacy.directory)
    assert len(await repo.get_messages(session.id)) == 1
    session.clear_messages()
    await repo.save(session)
    assert not (await repo.get(session.id)).recent_messages
    assert (await repo.get_messages(session.id))[0]["content"] == "remember this"
