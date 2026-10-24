import asyncio
import gc
import threading
import importlib
import sys
import weakref
from types import SimpleNamespace
from uuid import uuid4

import pytest
from PySide6.QtCore import QTimer
from src.core.application.orchestration.prompting.builder import PromptBuilder
from src.core.application.subsystems.memory.context import RecalledContext
from src.core.application.subsystems.memory.prompts import build_memory_section
from src.core.domain.entities.message import Message, MessageRole
from src.core.domain.entities.session import Session
from src.core.domain.value_objects.memory_fragment import MemoryFragment, MemorySource, MemoryZone
from src.core.infrastructure.providers.embeddings import SentenceTransformerEmbeddings
from src.core.infrastructure.providers.llm.local.provider import LlamaCppProvider
from src.core.infrastructure.repositories.sqlite_memory_repository import SQLiteMemoryRepository
from src.core.infrastructure.repositories.sqlite_session_repository import SQLiteSessionRepository
from test_runtime import qt_app  # noqa: F401, fixture
from test_subsystems import runtime  # noqa: F401, fixture


async def test_multi_zone_retrieval_encodes_query_once_and_filters_before_top_k(tmp_path):
    class Embeddings:
        model_id = "test"
        queries = 0
        async def embed_documents(self, texts):
            return [[1., 0.] for _ in texts]
        async def embed_query(self, text):
            self.queries += 1
            return [1., 0.]
    embeddings = Embeddings()
    repo = SQLiteMemoryRepository(tmp_path / "memory.sqlite3", embeddings)
    own, other = uuid4(), uuid4()
    for zone in (MemoryZone.USER_FACTS, MemoryZone.DIALOGUE):
        for uid, importance in ((other, 1), (own, .8)):
            await repo.upsert_fragment(MemoryFragment.create(
                zone=zone, content="tea", importance=importance, source=MemorySource.CONVERSATION,
                metadata={"user_id": str(uid)}))
    result = await repo.search_many("tea", {MemoryZone.USER_FACTS: 1, MemoryZone.DIALOGUE: 1}, own)
    assert embeddings.queries == 1
    assert all(len(rows) == 1 and rows[0].metadata["user_id"] == str(own) for rows in result.values())


async def test_index_rebuild_has_bounded_batches(tmp_path):
    batches = []
    class Embeddings:
        model_id = "test"
        async def embed_documents(self, texts):
            batches.append(len(texts))
            return [[1, 0] for _ in texts]
    repo = SQLiteMemoryRepository(tmp_path / "memory.sqlite3", Embeddings())
    fragments = [MemoryFragment.create(zone=MemoryZone.USER_FACTS, content=str(i),
                 importance=.8, source=MemorySource.CONVERSATION) for i in range(70)]
    assert len(await repo._index_fragments(fragments)) == 70
    assert batches == [32, 32, 6]
    await repo._index_fragments(fragments)
    assert batches == [32, 32, 6]


async def test_embedding_close_waits_for_cancelled_worker_and_releases_model():
    provider = SentenceTransformerEmbeddings()
    entered, release = threading.Event(), threading.Event()
    class Model:
        pass
    provider._model = Model()
    reference = weakref.ref(provider._model)
    def encode(texts):
        entered.set()
        assert release.wait(3)
        return [[1., 0.]]
    provider._encode = encode
    task = asyncio.create_task(provider.embed_query("hello"))
    while not entered.is_set():
        await asyncio.sleep(.001)
    task.cancel()
    close = asyncio.create_task(provider.close())
    await asyncio.sleep(.01)
    assert not close.done()
    task.cancel()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    await close
    gc.collect()
    assert reference() is None
    assert provider._executor is None


def test_context_budget_keeps_current_user_and_tool_exchange_and_counts_once():
    tokenizations = []
    calls = []
    def tokenize(data, **kwargs):
        tokenizations.append(data)
        return list(data)
    provider = LlamaCppProvider("unused", n_ctx=700)
    provider._llm = SimpleNamespace(tokenize=tokenize,
        create_chat_completion=lambda **kwargs: calls.append(kwargs))
    prompt = [{"role": "system", "content": "core"},
              {"role": "user", "content": "old" * 50},
              {"role": "assistant", "content": "old response" * 20},
              {"role": "user", "content": "current"},
              {"role": "assistant", "content": "<tool_call>echo</tool_call>"},
              {"role": "user", "content": "<|turn>tool\nresult<turn|>"}]
    provider._complete(prompt, .1, 100, False, {})
    assert len(tokenizations) == 6
    assert [m["content"] for m in calls[0]["messages"]] == [
        "core", "current", "<tool_call>echo</tool_call>", "<|turn>tool\nresult<turn|>"]


def test_context_overflow_never_drops_current_user():
    provider = LlamaCppProvider("unused", n_ctx=500)
    provider._llm = SimpleNamespace(tokenize=lambda data, **kw: list(data))
    prompt = [{"role": "system", "content": "core"}, {"role": "user", "content": "x" * 500}]
    with pytest.raises(ValueError, match="Контекст переполнен"):
        provider._complete(prompt, .1, 100, False, {})
    assert prompt[1]["content"] == "x" * 500


def test_memory_prompt_is_bounded_and_deduplicated():
    fragments = [MemoryFragment.create(zone=MemoryZone.DIALOGUE, content=str(i) + "x" * 500,
                 importance=.8, source=MemorySource.CONVERSATION) for i in range(20)]
    recalled = RecalledContext(dialogue_summaries=fragments, impactful=fragments)
    text = build_memory_section(recalled)
    assert len(text) <= 3600
    assert text.count(fragments[0].content) == 1


async def test_compression_does_not_lose_new_message_from_archive(tmp_path):
    repo = SQLiteSessionRepository(tmp_path / "sessions.sqlite3", tmp_path / "legacy")
    session = Session.start(uuid4())
    msg = Message(role=MessageRole.USER, content="archive me", session_id=session.id)
    session.add_message(msg)
    session.drop_oldest(1)
    await repo.save(session)
    assert not session.pending_messages
    assert not (await repo.get(session.id)).recent_messages
    assert (await repo.get_messages(session.id))[0]["content"] == "archive me"


async def test_pipeline_uses_one_analysis_and_one_recall(runtime):
    from unittest.mock import AsyncMock
    from src.core.application.commands.chat_commands import SendMessageCommand
    r = runtime
    r.llm.infer_json.return_value = {
        "emotion": {"emotion": "curious", "intensity": .3, "confidence": .9, "evidence": "чай"},
        "memories": [{"zone": "user_facts", "content": "Любит чай", "importance": .9,
                      "confidence": .9, "evidence": "люблю чай"}]}
    memory = r.c.memory_engine()
    memory.recall = AsyncMock(wraps=memory.recall)
    await r.c.chat_orchestration().process_user_message(SendMessageCommand(text="Я люблю чай"))
    assert r.llm.infer_json.await_count == 1
    assert memory.recall.await_count == 1
    assert len(r.prompts) == 1
    assert any(f.content == "Любит чай" for f in (await r.c.memory_repo().get_by_lina(r.lina.id)).all())


async def test_malformed_analysis_does_not_trigger_retry_or_store_facts(runtime):
    from src.core.application.commands.chat_commands import SendMessageCommand
    runtime.llm.infer_json.return_value = []
    await runtime.c.chat_orchestration().process_user_message(SendMessageCommand(text="Привет"))
    assert runtime.llm.infer_json.await_count == 1
    assert len(runtime.prompts) == 1
    assert not (await runtime.c.memory_repo().get_by_lina(runtime.lina.id)).all()


def test_bubble_reuses_owned_timers(qt_app):
    from src.core.presentation.desktop.qt.chibi.core.event_bus import EventBus
    from src.core.presentation.desktop.qt.chibi.viewmodels.bubble_viewmodel import BubbleViewModel
    from src.core.presentation.desktop.qt.chibi.views.bubble_view import BubbleView
    vm = BubbleViewModel(EventBus())
    view = BubbleView(vm)
    for _ in range(100):
        view._start_animation(20)
        view.hide_with_delay(1000)
    assert len(view.findChildren(QTimer)) == 3
    assert view._hold_timer.isActive()
    view.hide()
    view.close()
    view.deleteLater()
    vm.cleanup()


def test_camera_releases_native_resource_on_error(monkeypatch):
    released = []
    def fail(*args):
        raise RuntimeError("camera failure")
    fake = SimpleNamespace(VideoCapture=lambda i: SimpleNamespace(
        isOpened=lambda: True, get=fail, release=lambda: released.append(True)),
        CAP_PROP_FRAME_WIDTH=1)
    monkeypatch.setitem(sys.modules, "cv2", fake)
    sys.modules.pop("src.core.utils.camera", None)
    module = importlib.import_module("src.core.utils.camera")
    try:
        with pytest.raises(RuntimeError, match="camera failure"):
            module.list_cameras_opencv(1)
        assert released == [True]
    finally:
        sys.modules.pop("src.core.utils.camera", None)


def test_microphones_terminate_native_resource_on_error(monkeypatch):
    released = []
    def fail():
        raise RuntimeError("audio failure")
    monkeypatch.setitem(sys.modules, "pyaudio", SimpleNamespace(PyAudio=lambda: SimpleNamespace(
        get_device_count=fail, terminate=lambda: released.append(True))))
    sys.modules.pop("src.core.utils.audio", None)
    module = importlib.import_module("src.core.utils.audio")
    try:
        with pytest.raises(RuntimeError, match="audio failure"):
            module.get_microphones()
        assert released == [True]
    finally:
        sys.modules.pop("src.core.utils.audio", None)
