import base64
import json
import time
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from PIL import Image
from src.bootstrap.app import Application
from src.core.application.commands.chat_commands import SendMessageCommand
from src.core.application.ports.llm_port import ChatResponse
from src.core.application.subsystems.memory.relationship import relationship_score
from src.core.domain.entities.lina import Lina
from src.core.domain.entities.lina_memory import LinaMemory
from src.core.domain.entities.session import Session
from src.core.domain.value_objects.settings import Settings
from src.core.domain.value_objects.tool import ToolCall
from src.core.domain.value_objects.memory_fragment import MemoryZone
from src.core.infrastructure.services.media_processor import FileMediaProcessor
from test_runtime import prepare


@pytest.fixture
async def runtime(tmp_path):
    app = Application()
    prompts = []
    async def stream(messages, **kwargs):
        prompts.append(messages)
        yield "Мне страшно. "
        yield "Убери паука, пожалуйста."
    llm = SimpleNamespace(initialize=AsyncMock(), close=AsyncMock(), stream_generate=stream,
                          infer_json=AsyncMock(), generate=AsyncMock(return_value=ChatResponse("На картинке паук")))
    prepare(app, tmp_path, llm)
    app._container.set_settings(Settings.default())
    container = app._container.container
    lina = await app._container.ensure_lina()
    user = await app._container.ensure_user()
    session = await app._container.ensure_session(user.id)
    yield SimpleNamespace(app=app, c=container, llm=llm, lina=lina, user=user, session=session, prompts=prompts)
    await app._container.reset()


async def test_image_to_emotion_memory_persistence_and_relationship(runtime, tmp_path):
    r = runtime
    picture = tmp_path / "attachment.png"
    Image.new("RGB", (32, 32)).save(picture)
    scores = []
    for _ in range(2):
        r.llm.infer_json.return_value = {
            "emotion": {"emotion": "fear", "intensity": .9, "confidence": .95, "evidence": "паук"},
            "memories": [{"zone": "identity_facts", "content": "Больше не боюсь пауков",
                          "importance": 1, "confidence": 1, "evidence": "паук"}],
        }
        await r.c.chat_orchestration().process_user_message(SendMessageCommand(
            text="Смотри", data_files=[{"path": str(picture)}]))
        lina = await r.c.lina_repo().get()
        lina._memory = await r.c.memory_repo().get_by_lina(lina.id)
        scores.append(relationship_score(lina, r.user.id, r.c.policy()))
    assert scores[1] < scores[0] < 0
    assert len(lina.memory.all()) == 2
    assert not lina.memory.by_zone(MemoryZone.IDENTITY_FACTS)
    session = await r.c.session_repo().get(r.session.id)
    assert len(session.recent_messages) == 4
    assert "паук" in session.recent_messages[0].content
    assert "base64" not in json.dumps([m.content for m in session.recent_messages])
    assert (await r.c.user_repo().get_default()).interaction_count == 2
    assert "паук" in r.prompts[-1][0].content
    assert r.llm.infer_json.await_count == 2  # One analysis per turn, not emotion + extraction.


@pytest.mark.parametrize("bad", [None, [], {}, "unknown"])
async def test_memory_rejects_invalid_zone(runtime, bad):
    r = runtime
    result = await r.c.memory_engine().apply_extraction([
        {"zone": bad, "content": "test", "evidence": "test", "importance": 1, "confidence": 1}
    ], r.lina, r.user.id, uuid4(), "test")
    assert result == []


async def test_memory_thresholds_evidence_capacity_and_deduplication(runtime):
    r = runtime
    fragment = {"zone": "user_facts", "content": "Любит чай", "evidence": "чай", "importance": .9, "confidence": .9}
    rows = [dict(fragment, confidence=.2), dict(fragment, evidence="кофе"),
            dict(fragment, importance=float("nan")), fragment, fragment]
    memory = r.c.memory_engine()
    accepted = await memory.apply_extraction(rows, r.lina, r.user.id, uuid4(), "люблю чай")
    assert len(accepted) == 1
    assert len(r.lina.memory.all()) == 1
    await r.c.memory_repo().save(r.lina.memory)
    restored = await r.c.memory_repo().get_by_lina(r.lina.id)
    assert restored.all()[0].id == accepted[0].id
    with pytest.raises(ValueError, match="another Lina"):
        await r.c.memory_repo().save(LinaMemory(uuid4()))


async def test_compression_has_user_scope(runtime):
    r = runtime
    await r.c.memory_engine().apply_compression("Личный диалог", r.session, r.lina, 0)
    result = await r.c.memory_engine().recall("Личный", r.lina, uuid4())
    assert not result.dialogue_summaries
    result = await r.c.memory_engine().recall("Личный", r.lina, r.user.id)
    assert len(result.dialogue_summaries) == 1


async def test_tool_arguments_and_unknown_tools(runtime):
    engine = runtime.c.tool_engine()
    for call in (ToolCall("missing"), ToolCall("echo"), ToolCall("echo", {"text": 12}),
                 ToolCall("echo", {"text": "hello", "extra": True})):
        assert not (await engine.execute(call, runtime.user)).success
    result = await engine.execute(ToolCall("echo", {"text": "hello"}), runtime.user)
    assert result.success and "hello" in result.output


async def test_stream_tool_marker_is_not_shown_to_user(runtime):
    r = runtime
    chunks = []
    async def stream(*args, **kwargs):
        for part in ['Сейчас ', '<tool_', 'call>{"name":"echo","arguments":{"text":"hello"}}', '</tool_call>']:
            yield part
    r.llm.stream_generate = stream
    bus = r.c.event_bus()
    from src.core.domain.events.message_events import StreamChunk
    bus.subscribe(StreamChunk, lambda event: chunks.append(event.chunk))
    await bus.start()
    try:
        result = await r.c.pipeline()._stream_and_detect_tool([], r.session)
        await bus.drain()
        assert "".join(chunks) == "Сейчас "
        assert result.tool_call.name == "echo"
    finally:
        await bus.stop()


async def test_autonomy_discards_action_when_user_returns(runtime):
    r = runtime
    autonomy = r.c.autonomy_orchestration()
    gate = r.c.gate()
    gate.last_user_activity = time.monotonic() - 600
    async def thought(*args, **kwargs):
        gate.touch()
        return {"thought": "Прогуляюсь", "confidence": .9, "action": {"type": "move", "content": "left"}}
    r.llm.infer_json.side_effect = thought
    bus = r.c.event_bus()
    actions = []
    from src.core.domain.events.desktop_events import DesktopActionRequested
    bus.subscribe(DesktopActionRequested, actions.append)
    await bus.start()
    try:
        await autonomy._tick(r.lina, r.user, r.session)
        await bus.drain()
        assert not actions
    finally:
        await bus.stop()


def test_image_normalization_and_audio_encoding(tmp_path):
    media = FileMediaProcessor()
    picture = tmp_path / "image.png"
    Image.new("RGBA", (1800, 900)).save(picture)
    part = media.build_media_part(str(picture))
    data = base64.b64decode(part["image_url"]["url"].split(",", 1)[1])
    with Image.open(BytesIO(data)) as image:
        assert image.size == (1280, 640)
    audio = tmp_path / "voice.wav"
    audio.write_bytes(b"test audio")
    part = media.build_media_part(str(audio))
    assert base64.b64decode(part["input_audio"]["data"]) == b"test audio"


async def test_reconsideration_preserves_event_and_requires_new_evidence(runtime):
    from src.core.domain.entities.message import Message, MessageRole
    from src.core.domain.value_objects.emotion import Emotion, EmotionType
    r = runtime
    message = Message(role=MessageRole.USER, content="паук", session_id=r.session.id)
    r.lina.current_emotion = Emotion.from_type(EmotionType.FEAR, .9)
    engine = r.c.memory_engine()
    await engine.remember_emotion(r.lina, r.user, message, "паук",
                                 {"emotion": "fear", "intensity": .9, "confidence": .95, "evidence": "паук"})
    original = r.lina.memory.all()[0]
    update_id = uuid4()
    candidate = {"memory_id": str(original.id), "confidence": .95,
                 "evidence": "не хотел пугать", "interpretation": "Пользователь объяснил отсутствие намерения напугать",
                 "relationship_weight": 0}
    assert not await engine.reconsider_episode(candidate, r.lina, r.user.id, update_id, "привет")
    assert await engine.reconsider_episode(candidate, r.lina, r.user.id, update_id, "Я не хотел пугать")
    assert not await engine.reconsider_episode(candidate, r.lina, r.user.id, update_id, "Я не хотел пугать")
    updated = r.lina.memory.all()[0]
    assert updated.content == original.content
    assert updated.emotional_intensity == original.emotional_intensity
    assert len(updated.metadata["interpretations"]) == 1
    assert relationship_score(r.lina, r.user.id, r.c.policy()) == 0
    stored = await r.c.memory_repo().get_by_lina(r.lina.id)
    assert stored.all()[0].metadata["interpretations"][0]["evidence"] == "не хотел пугать"
