import asyncio
import os
from unittest.mock import AsyncMock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from src.core.application.commands.speech_commands import RecognizeSpeechCommand
from src.core.application.commands.chat_commands import SendMessageCommand
from src.core.application.handlers.speech_handler import RecognizeSpeechHandler
from src.core.application.orchestration.runtime_gate import RuntimeGate
from src.core.domain.events.speech_events import SpeechRecognized, SpeechRecognitionFailed
from src.core.infrastructure.providers.command_bus import CommandBus
from src.core.infrastructure.providers.event_bus import EventBus


async def test_application_recognizes_recording_and_publishes_result():
    recognizer, bus = AsyncMock(), AsyncMock()
    recognizer.transcribe.return_value = "  Привет Лина  "
    handler = RecognizeSpeechHandler(recognizer, bus, RuntimeGate())
    await handler.handle(RecognizeSpeechCommand("request", bytes(3200), 16000))
    recognizer.transcribe.assert_awaited_once_with(bytes(3200), 16000)
    event = bus.publish.await_args.args[0]
    assert isinstance(event, SpeechRecognized)
    assert event.request_id == "request" and event.text == "Привет Лина"


@pytest.mark.parametrize("pcm,rate", [(b"", 16000), (b"1", 16000), (b"12", True),
                                      (b"12", 0), (b"12", 96000), (bytes(16000 * 2 * 60 + 2), 16000)],
                         ids=["empty", "unaligned", "boolean-rate", "zero-rate", "unsupported-rate", "too-long"])
async def test_invalid_recordings_never_reach_provider(pcm, rate):
    recognizer, bus = AsyncMock(), AsyncMock()
    handler = RecognizeSpeechHandler(recognizer, bus, RuntimeGate())
    await handler.handle(RecognizeSpeechCommand("invalid", pcm, rate))
    recognizer.transcribe.assert_not_called()
    event = bus.publish.await_args.args[0]
    assert isinstance(event, SpeechRecognitionFailed) and event.request_id == "invalid"


@pytest.mark.parametrize("failure", ["", "   ", RuntimeError("Vosk unavailable")])
async def test_empty_transcript_and_provider_failure_are_application_events(failure):
    recognizer, bus = AsyncMock(), AsyncMock()
    if isinstance(failure, Exception):
        recognizer.transcribe.side_effect = failure
    else:
        recognizer.transcribe.return_value = failure
    handler = RecognizeSpeechHandler(recognizer, bus, RuntimeGate())
    await handler.handle(RecognizeSpeechCommand("failed", bytes(320), 16000))
    event = bus.publish.await_args.args[0]
    assert isinstance(event, SpeechRecognitionFailed)
    assert event.error == ("Vosk unavailable" if isinstance(failure, Exception) else "Речь не распознана. Попробуйте ещё раз.")


async def test_stopping_runtime_rejects_recognition_and_cancellation_does_not_publish_text():
    gate, bus, recognizer = RuntimeGate(), AsyncMock(), AsyncMock()
    handler = RecognizeSpeechHandler(recognizer, bus, gate)
    gate.stopping = True
    await handler.handle(RecognizeSpeechCommand("stopped", bytes(320)))
    recognizer.transcribe.assert_not_called()
    assert isinstance(bus.publish.await_args.args[0], SpeechRecognitionFailed)
    gate.stopping = False
    bus.reset_mock()
    entered = asyncio.Event()
    async def transcribe(*args):
        entered.set()
        await asyncio.Event().wait()
    recognizer.transcribe.side_effect = transcribe
    task = asyncio.create_task(handler.handle(RecognizeSpeechCommand("cancel", bytes(320))))
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    bus.publish.assert_not_called()
    assert not gate.lock.locked()


async def test_ui_sends_command_and_only_routes_its_own_result_events():
    from PySide6.QtWidgets import QApplication
    from src.core.presentation.desktop.qt.chibi.services.api_service import ApiService
    from src.core.presentation.desktop.qt.chibi.core.event_bus import EventBus as PresentationBus
    from src.core.presentation.desktop.qt.chibi.core.event_types import EventType
    app = QApplication.instance() or QApplication([])
    commands, system, ui = CommandBus(), EventBus(), PresentationBus()
    recognizer = AsyncMock()
    recognizer.transcribe.return_value = "Привет"
    recognition = RecognizeSpeechHandler(recognizer, system, RuntimeGate())
    chat = AsyncMock()
    commands.register(RecognizeSpeechCommand, recognition)
    commands.register(SendMessageCommand, chat)
    api = ApiService(ui, commands, system)
    api._async_task_timer.stop()
    errors = []
    ui.subscribe(EventType.AI_ERROR_OCCURRED, lambda event: errors.append(event.data))
    await system.start()
    try:
        assert not hasattr(api, "speech_recognizer")
        api._on_recording_ready(bytes(320), 16000)
        recognizer.transcribe.assert_not_called()  # UI only enqueued a command.
        api._process_async_queue()
        await asyncio.gather(*list(api._tasks))
        await system.drain()
        api._process_async_queue()
        await asyncio.gather(*list(api._tasks))
        assert chat.handle.await_count == 1
        assert chat.handle.await_args.args[0].text == "Привет"
        assert not api._recognition_requests
        await system.publish(SpeechRecognized(request_id="other-window", text="foreign"))
        await system.publish(SpeechRecognitionFailed(request_id="other-window", error="foreign"))
        await system.drain()
        assert not api._async_task_queue and not errors
        recognizer.transcribe.return_value = ""
        api._on_recording_ready(bytes(320), 16000)
        api._process_async_queue()
        await asyncio.gather(*list(api._tasks))
        await system.drain()
        assert len(errors) == 1 and "не распознана" in errors[0]
        assert chat.handle.await_count == 1
    finally:
        await api.aclose()
        recognizer.close.assert_not_called()  # Provider ownership belongs to DI.
        assert system.get_stats()["handlers_count"] == 0
        await system.stop()
        api.deleteLater()
        app.processEvents()


async def test_di_closes_and_rebinds_recognizer_after_stop(tmp_path):
    from dependency_injector import providers
    from src.bootstrap.di import ApplicationContainer
    from src.core.domain.value_objects.settings import Settings
    container = ApplicationContainer()
    settings = Settings.default()
    settings.vosk_model_path = str(tmp_path / "vosk")
    container.set_settings(settings)
    recognizer = container.container.speech_recognizer()
    assert recognizer.model_path == tmp_path / "vosk"
    container.get_command_bus()
    container.container.llm.override(providers.Object(AsyncMock()))
    container.container.embeddings.override(providers.Object(AsyncMock()))
    await container.reset()
    assert recognizer._closed
    fresh = container.container.speech_recognizer()
    assert fresh is not recognizer and not fresh._closed
    assert container.get_command_bus()._handlers[RecognizeSpeechCommand]._recognizer is fresh
    await fresh.close()
