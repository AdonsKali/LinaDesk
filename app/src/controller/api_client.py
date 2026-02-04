import json
import threading
import websocket
import logging
import pyaudio
from settings import json_config
from typing import Callable

logger = logging.getLogger(__name__)


class APIClient:
    def __init__(self, base_url=f"http://{json_config['host']}:{json_config['port']}"):
        self.base_url = base_url
        self.agent_ws_url = base_url.replace("http://", "ws://") + "/ws/agent"
        self.recognition_ws_url = base_url.replace("http://", "ws://") + "/ws/recognition"

        self.agent_ws = None
        self.recognition_ws = None
        self.agent_thread = None
        self.recognition_thread = None

        # ASR state
        self._recording = False
        self._stream = None
        self._pyaudio = None
        
        # Callbacks
        self.on_agent_token = None
        self.on_agent_complete = None
        self.on_agent_error = None
        self.on_recognition_result = None
        self.on_recognition_error = None

    def connect_agent(self):
        """Подключение к WebSocket агента"""
        def run():
            self.agent_ws = websocket.WebSocketApp(
                self.agent_ws_url,
                on_open=self._on_agent_open,
                on_message=self._on_agent_message,
                on_error=self._on_agent_error,
                on_close=self._on_agent_close,
            )
            self.agent_ws.run_forever(ping_interval=80, ping_timeout=60)

        self.agent_thread = threading.Thread(target=run, daemon=True)
        self.agent_thread.start()

    def connect_recognition(self):
        """Подключение к WebSocket распознавания"""
        def run():
            self.recognition_ws = websocket.WebSocketApp(
                self.recognition_ws_url,
                on_open=self._on_recognition_open,
                on_message=self._on_recognition_message,
                on_error=self._on_recognition_error,
                on_close=self._on_recognition_close,
            )
            self.recognition_ws.run_forever(ping_interval=80, ping_timeout=60)

        self.recognition_thread = threading.Thread(target=run, daemon=True)
        self.recognition_thread.start()

    def close_all(self):
        """Закрыть все соединения"""
        if self.agent_ws:
            self.agent_ws.close()
        if self.recognition_ws:
            self.recognition_ws.close()

    def set_agent_callbacks(self, on_token: Callable, on_complete: Callable, on_error: Callable):
        """Установить колбэки для агента"""
        self.on_agent_token = on_token
        self.on_agent_complete = on_complete
        self.on_agent_error = on_error

    def set_recognition_callbacks(self, on_result: Callable, on_error: Callable):
        """Установить колбэки для распознавания"""
        self.on_recognition_result = on_result
        self.on_recognition_error = on_error

    def send_agent_json(self, data: dict):
        """Отправить JSON сообщение агенту"""
        if self.agent_ws:
            self.agent_ws.send(json.dumps(data))

    def send_recognition_json(self, data: dict):
        """Отправить JSON сообщение сервису распознавания"""
        if self.recognition_ws:
            self.recognition_ws.send(json.dumps(data))

    def send_recognition_bytes(self, data: bytes):
        """Отправить байты сервису распознавания"""
        if self.recognition_ws:
            self.recognition_ws.send(data, opcode=websocket.ABNF.OPCODE_BINARY)

    def generate_text(self, prompt: str):
        """Генерация текста через агента"""
        self.send_agent_json({
            "type": "user_text",
            "prompt": prompt
        })

    def start_recognition(self, sample_rate: int = 16000):
        """Начать распознавание речи"""
        self.send_recognition_json({
            "type": "recognize_start",
            "sample_rate": sample_rate
        })
        self._start_recording()

    def stop_recognition(self):
        """Остановить распознавание речи"""
        self._stop_recording()
        if self.recognition_ws:
            self.send_recognition_json({"type": "recognize_final"})

    # Agent WebSocket handlers
    def _on_agent_open(self, ws):
        logger.info("✅ Agent WebSocket connected")

    def _on_agent_message(self, ws, message):
        if isinstance(message, (bytes, bytearray)):
            return

        try:
            data = json.loads(message)
        except Exception:
            return

        msg_type = data.get("type")

        if msg_type == "token":
            if self.on_agent_token:
                self.on_agent_token(data.get("token", ""))

        elif msg_type == "complete":
            if self.on_agent_complete:
                self.on_agent_complete()

        elif msg_type == "error":
            if self.on_agent_error:
                self.on_agent_error(data.get("message", "error"))

    def _on_agent_error(self, ws, error):
        logger.error(f"Agent WebSocket error: {error}")
        if self.on_agent_error:
            self.on_agent_error(str(error))

    def _on_agent_close(self, ws, code, reason):
        logger.info("Agent WebSocket closed")

    def _on_recognition_open(self, ws):
        logger.info("Recognition WebSocket connected")

    def _on_recognition_message(self, ws, message):
        if isinstance(message, (bytes, bytearray)):
            return

        try:
            data = json.loads(message)
        except Exception:
            return

        msg_type = data.get("type")

        if msg_type == "recognition_result":
            if self.on_recognition_result:
                self.on_recognition_result(data.get("text", ""))
                self._stop_recording()

        elif msg_type == "recognition_started":
            logger.info("Recognition started successfully")

        elif msg_type == "error":
            if self.on_recognition_error:
                self.on_recognition_error(data.get("message", "error"))

    def _on_recognition_error(self, ws, error):
        logger.error(f"Recognition WebSocket error: {error}")
        if self.on_recognition_error:
            self.on_recognition_error(str(error))

    def _on_recognition_close(self, ws, code, reason):
        logger.info("Recognition WebSocket closed")
        self._stop_recording()

    # Audio recording methods
    def _start_recording(self):
        if self._recording:
            return

        self._recording = True
        self._pyaudio = pyaudio.PyAudio()

        self._stream = self._pyaudio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=4000
        )

        def loop():
            try:
                while self._recording:
                    data = self._stream.read(4000, exception_on_overflow=False)
                    self.send_recognition_bytes(data)
            finally:
                try:
                    self.send_recognition_json({"type": "recognize_final"})
                except Exception:
                    pass

        threading.Thread(target=loop, daemon=True).start()

    def _stop_recording(self):
        if not self._recording:
            return

        self._recording = False

        try:
            if self._stream:
                self._stream.stop_stream()
                self._stream.close()
            if self._pyaudio:
                self._pyaudio.terminate()
        except Exception:
            pass