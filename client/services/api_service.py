# services/api_service.py
"""
Client for communicating with the local server API
"""
import json
import threading
import websocket
import logging
import pyaudio
from PySide6.QtCore import QObject, Signal
from typing import Callable

logger = logging.getLogger(__name__)


class APIClient(QObject):
    """Client for API communication with the AI server via WebSockets"""
    
    # Signals for various events
    tool_call_received = Signal()
    token_received = Signal(str)
    generation_complete = Signal()
    generation_error = Signal(str)
    recognition_result = Signal(str)
    recognition_error = Signal(str)
    connected = Signal()
    disconnected = Signal()

    def __init__(self, base_url=f"http://localhost:8000"):
        super().__init__()
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

    def connect(self):
        """Connect to both WebSocket services"""
        self.connect_agent()
        self.connect_recognition()

    def connect_agent(self):
        """Connect to the agent WebSocket"""
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
        """Connect to the recognition WebSocket"""
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
        """Close all connections"""
        if self.agent_ws:
            self.agent_ws.close()
        if self.recognition_ws:
            self.recognition_ws.close()

    def send_message(self, text: str):
        """Send a message to the agent for processing"""
        if self.agent_ws:
            self.agent_ws.send(json.dumps({
                "type": "user_text",
                "prompt": text
            }))
        else:
            logger.warning("Agent WebSocket not connected")

    def start_voice_recognition(self, sample_rate: int = 16000):
        """Start voice recognition"""
        if self.recognition_ws:
            self.recognition_ws.send(json.dumps({
                "type": "recognize_start",
                "sample_rate": sample_rate
            }))
            self._start_recording()
        else:
            logger.warning("Recognition WebSocket not connected")

    def stop_voice_recognition(self):
        """Stop voice recognition"""
        self._stop_recording()
        if self.recognition_ws:
            self.recognition_ws.send(json.dumps({"type": "recognize_final"}))

    # Agent WebSocket handlers
    def _on_agent_open(self, ws):
        logger.info("Agent WebSocket connected")
        self.connected.emit()

    def _on_agent_message(self, ws, message):
        if isinstance(message, (bytes, bytearray)):
            return

        try:
            data = json.loads(message)
        except Exception as e:
            logger.error(f"Error parsing agent message: {e}")
            return

        msg_type = data.get("type")

        if msg_type == "token":
            token = data.get("content", "")
            if token:
                self.token_received.emit(token)

        elif msg_type == "tool_call":
            self.tool_call_received.emit()

        elif msg_type == "complete":
            self.generation_complete.emit()

        elif msg_type == "error":
            error_msg = data.get("message", "Unknown error")
            self.generation_error.emit(error_msg)

    def _on_agent_error(self, ws, error):
        logger.error(f"Agent WebSocket error: {error}")
        self.generation_error.emit(str(error))

    def _on_agent_close(self, ws, code, reason):
        logger.info("Agent WebSocket closed")
        self.disconnected.emit()

    # Recognition WebSocket handlers
    def _on_recognition_open(self, ws):
        logger.info("Recognition WebSocket connected")

    def _on_recognition_message(self, ws, message):
        if isinstance(message, (bytes, bytearray)):
            return

        try:
            data = json.loads(message)
        except Exception as e:
            logger.error(f"Error parsing recognition message: {e}")
            return

        msg_type = data.get("type")

        if msg_type == "complete":
            text = data.get("content", "")
            self.recognition_result.emit(text)
            self._stop_recording()

        elif msg_type == "start":
            logger.info("Recognition started successfully")

        elif msg_type == "error":
            error_msg = data.get("message", "Recognition error")
            self.recognition_error.emit(error_msg)

    def _on_recognition_error(self, ws, error):
        logger.error(f"Recognition WebSocket error: {error}")
        self.recognition_error.emit(str(error))

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
                    data = self._stream.read(4000, exception_on_overflow=False) #type: ignore
                    if self.recognition_ws:
                        self.recognition_ws.send(data, opcode=websocket.ABNF.OPCODE_BINARY)
            except Exception as e:
                logger.error(f"Error during recording: {e}")
            finally:
                try:
                    if self.recognition_ws:
                        self.recognition_ws.send(json.dumps({"type": "finish"}))
                except Exception as e:
                    logger.error(f"Error sending final recognition message: {e}")

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
        except Exception as e:
            logger.error(f"Error stopping recording: {e}")