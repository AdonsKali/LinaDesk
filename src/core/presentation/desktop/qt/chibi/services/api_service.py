import asyncio
from src.core.utils.logger import logger
from typing import Callable, List, Tuple
from uuid import uuid4

from PySide6.QtCore import Signal, QTimer

from src.core.application.commands.speech_commands import RecognizeSpeechCommand
from src.core.domain.events.speech_events import SpeechRecognized, SpeechRecognitionFailed
from src.core.application.ports.command_bus import CommandBusPort
from src.core.application.ports.event_port import EventBusPort
from src.core.domain.events.message_events import (
    MessageProcessed,
    MessageReceived,
    StreamChunk,
    ResponseGenerated,
)
from src.core.domain.events.system_events import SystemError
from src.core.domain.events.tool_events import ToolExecution, ToolExecuted
from ..core.events import Event, EventType
from .base_service import BaseService
from .audio_recorder import AudioRecorder

logger = logger.get(__name__)


class ApiService(BaseService):
    """
    Мост между presentation (Chibi) и application.

    - Принимает UI-события из presentation EventBus (sync).
    - Отправляет команды через CommandBus (async, через очередь).
    - Подписан на SystemEventBus, транслирует в UI-сигналы.
    """

    _token_received = Signal(str)
    _response_started = Signal()
    _tool_call_started = Signal()
    _tool_call_completed = Signal()
    _generation_completed = Signal()
    _generation_error = Signal(str)
    _recognition_result = Signal(dict)
    _recognition_error = Signal(str)

    def __init__(
        self,
        presentation_event_bus,
        command_bus: CommandBusPort,
        system_event_bus: EventBusPort,
    ):
        super().__init__(presentation_event_bus)
        self._command_bus = command_bus
        self._system_event_bus = system_event_bus

        self._recorder: AudioRecorder | None = None
        self._is_recording = False
        self._closed = False
        self._tasks = set()
        self.microphone = None
        self._recognition_requests = set()
        self.activity_callback = lambda: None
        self._activity_timer = QTimer(self)
        self._activity_timer.setInterval(1000)
        self._activity_timer.timeout.connect(lambda: self.activity_callback())

        self._async_task_queue = []
        self._async_task_timer = QTimer(self)
        self._async_task_timer.setSingleShot(False)
        self._async_task_timer.timeout.connect(self._process_async_queue)
        self._async_task_timer.start(10)

        self._system_subscriptions: List[Tuple[type, Callable]] = []

        self._subscribe_to_system_events()
        self._setup_ui_handlers()
        self._setup_signals()

    # ==================== Signals → presentation bus ====================

    def _setup_signals(self) -> None:
        self._token_received.connect(
            lambda token: self._event_bus.emit(
                Event(EventType.AI_TOKEN_RECEIVED, str(token))
            )
        )
        self._response_started.connect(
            lambda: self._event_bus.emit(Event(EventType.AI_RESPONSE_STARTED))
        )
        self._tool_call_started.connect(
            lambda: self._event_bus.emit(Event(EventType.AI_TOOL_CALL_STARTED))
        )
        self._tool_call_completed.connect(
            lambda: self._event_bus.emit(Event(EventType.AI_TOOL_CALL_COMPLETED))
        )
        self._generation_completed.connect(
            lambda: self._event_bus.emit(Event(EventType.AI_RESPONSE_COMPLETED))
        )
        self._generation_error.connect(
            lambda error: self._event_bus.emit(
                Event(EventType.AI_ERROR_OCCURRED, str(error))
            )
        )
        self._recognition_result.connect(
            lambda text: self._event_bus.emit(
                Event(EventType.USER_TEXT_SUBMITTED, dict(text))
            )
        )
        self._recognition_error.connect(
            lambda error: self._event_bus.emit(
                Event(EventType.AI_ERROR_OCCURRED, str(error))
            )
        )

    # ==================== SystemEventBus subscriptions ====================

    def _subscribe(self, event_type, handler) -> None:
        self._system_event_bus.subscribe(event_type, handler)
        self._system_subscriptions.append((event_type, handler))

    def _subscribe_to_system_events(self) -> None:
        self._subscribe(StreamChunk, self._on_stream_chunk)
        self._subscribe(MessageProcessed, self._on_message_processed)
        self._subscribe(MessageReceived, self._on_message_received)
        self._subscribe(SystemError, self._on_system_error)
        self._subscribe(ToolExecution, self._on_tool_execution)
        self._subscribe(ToolExecuted, self._on_tool_executed)
        self._subscribe(ResponseGenerated, self._on_response_generated)
        self._subscribe(SpeechRecognized, self._on_speech_recognized)
        self._subscribe(SpeechRecognitionFailed, self._on_speech_recognition_failed)
        logger.info("ApiService subscribed to system events")

    # ==================== UI handlers (sync!) ====================

    def _setup_ui_handlers(self) -> None:
        self._event_bus.subscribe(
            EventType.USER_TEXT_SUBMITTED, self._on_user_text_submitted
        )
        self._event_bus.subscribe(
            EventType.USER_VOICE_STARTED, self._on_user_voice_started
        )
        self._event_bus.subscribe(
            EventType.USER_VOICE_STOPPED, self._on_user_voice_stopped
        )

    def _on_user_text_submitted(self, event: Event) -> None:
        data = event.data or {}
        text = data.get("text", "")
        data_files = data.get("data_files", [])
        if not text and not data_files:
            return

        from src.core.application.commands.chat_commands import SendMessageCommand
        command = SendMessageCommand(text=text, data_files=data_files)
        self._send_command_async(command)
        logger.info(f"User text submitted: {text[:50]!r}")

    def _on_user_voice_started(self, event: Event) -> None:
        self.start_recording()

    def _on_user_voice_stopped(self, event: Event) -> None:
        self.stop_recording()

    # ==================== System handlers (async) ====================

    async def _on_stream_chunk(self, event: StreamChunk) -> None:
        self._token_received.emit(event.chunk)

    async def _on_message_processed(self, event: MessageProcessed) -> None:
        self._generation_completed.emit()
        logger.info("Message processing completed")

    async def _on_response_generated(self, event: ResponseGenerated) -> None:
        if event.agent_id == "autonomy":
            self._response_started.emit()
            self._token_received.emit(event.message.content)
            self._generation_completed.emit()

    async def _on_message_received(self, event: MessageReceived) -> None:
        self._response_started.emit()
        logger.info("Message received by system")

    async def _on_tool_execution(self, event: ToolExecution) -> None:
        self._tool_call_started.emit()

    async def _on_tool_executed(self, event: ToolExecuted) -> None:
        self._tool_call_completed.emit()

    async def _on_system_error(self, event: SystemError) -> None:
        self._generation_error.emit(event.error)
        logger.error(f"System error: {event.error}")

    # ==================== Commands ====================

    def start_recording(self, sample_rate: int = 16000) -> None:
        if self._recorder or self._closed:
            return
        self.activity_callback()
        self._activity_timer.start()
        self._recorder = AudioRecorder(sample_rate, self.microphone)
        self._recorder.recording_ready.connect(self._on_recording_ready)
        self._recorder.error_occurred.connect(self._on_recorder_error)
        self._recorder.finished.connect(self._on_recorder_finished)
        self._recorder.start()
        self._is_recording = True

    def stop_recording(self) -> None:
        self._is_recording = False
        if self._recorder:
            self._recorder.stop()

    # ==================== Async queue ====================

    def _send_command_async(self, command) -> bool:
        if self._closed:
            return False
        if len(self._tasks) + len(self._async_task_queue) >= 4:
            self._generation_error.emit("Дождитесь завершения предыдущих запросов.")
            return False
        async def send():
            try:
                return await self._command_bus.send(command)
            except Exception as e:
                logger.error(f"Command {type(command).__name__} failed")
                if isinstance(command, RecognizeSpeechCommand):
                    self._recognition_requests.discard(command.request_id)
                    self._recognition_error.emit(str(e))
                else:
                    self._generation_error.emit(str(e))

        self._async_task_queue.append(send)
        return True

    def _process_async_queue(self) -> None:
        if not self._async_task_queue:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            logger.error("No running asyncio loop; dropping %d tasks",
                         len(self._async_task_queue))
            self._async_task_queue.clear()
            self._recognition_requests.clear()
            return

        tasks = self._async_task_queue.copy()
        self._async_task_queue.clear()
        for task in tasks:
            running = loop.create_task(task())
            self._tasks.add(running)
            running.add_done_callback(self._tasks.discard)

    # ==================== Audio ====================

    def _on_recording_ready(self, data: bytes, sample_rate: int):
        if self._closed:
            return
        request_id = uuid4().hex
        self._recognition_requests.add(request_id)
        if not self._send_command_async(RecognizeSpeechCommand(request_id, data, sample_rate)):
            self._recognition_requests.discard(request_id)

    async def _on_speech_recognized(self, event: SpeechRecognized):
        if not self._closed and event.request_id in self._recognition_requests:
            self._recognition_requests.discard(event.request_id)
            self.activity_callback()
            self._recognition_result.emit({"text": event.text, "data_files": []})

    async def _on_speech_recognition_failed(self, event: SpeechRecognitionFailed):
        if not self._closed and event.request_id in self._recognition_requests:
            self._recognition_requests.discard(event.request_id)
            self._recognition_error.emit(event.error)

    def _on_recorder_error(self, error: str) -> None:
        logger.error(f"Recorder error: {error}")
        self._recognition_error.emit(error)

    def _on_recorder_finished(self) -> None:
        self._activity_timer.stop()
        self._is_recording = False
        if not self._closed:
            self._event_bus.emit(Event(EventType.VOICE_CAPTURE_FINISHED))
        if self._recorder:
            self._recorder.deleteLater()
        self._recorder = None

    # ==================== Lifecycle ====================

    def initialize(self) -> None:
        logger.info("ApiService initialized")

    async def aclose(self):
        self._closed = True
        self._activity_timer.stop()
        self._async_task_timer.stop()
        self._async_task_queue.clear()
        self.stop_recording()
        # Keep the Qt loop alive until the recorder exits.
        while self._recorder and self._recorder.isRunning():
            await asyncio.sleep(0.02)
        tasks = list(self._tasks)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self.cleanup()

    def cleanup(self) -> None:
        logger.info("Cleaning up ApiService")
        self._closed = True
        self._recognition_requests.clear()
        self._activity_timer.stop()
        self._async_task_timer.stop()
        self._async_task_queue.clear()
        self.stop_recording()
        if self._recorder:
            self._recorder.wait()
        for task in self._tasks:
            task.cancel()

        for event_type, handler in self._system_subscriptions:
            try:
                self._system_event_bus.unsubscribe(event_type, handler)
            except Exception:
                pass
        self._system_subscriptions.clear()

        # Отписываемся от presentation
        for et in (
            EventType.USER_TEXT_SUBMITTED,
            EventType.USER_VOICE_STARTED,
            EventType.USER_VOICE_STOPPED,
        ):
            try:
                self._event_bus.unsubscribe(et, getattr(self, f"_on_{et.name.lower()}"))
            except Exception:
                pass

        logger.info("ApiService cleanup complete")
