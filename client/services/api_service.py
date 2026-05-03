import json
import threading
import queue
import websocket
import logging
from PySide6.QtCore import Signal
from client.core.event_bus import EventBus
from client.core.events import Event
from client.core.event_types import EventType
from .base_service import BaseService
from .audio_recorder import AudioRecorder

logger = logging.getLogger(__name__)

class ApiService(BaseService):
    """Сервис для работы с API сервера"""
    
    _token_received = Signal(str)
    _tool_call_started = Signal()
    _tool_call_completed = Signal()
    _generation_completed = Signal()
    _generation_error = Signal(str)
    _recognition_result = Signal(str)
    _recognition_error = Signal(str)
    _connection_lost = Signal(str)
    _send_audio_chunk_signal = Signal(bytes)
    
    def __init__(self, event_bus: EventBus, base_url: str = "http://localhost:8000"):
        super().__init__(event_bus)
        self.base_url = base_url
        self.agent_ws = None
        self.recognition_ws = None
        
        self._recorder = None
        
        self._should_reconnect = True
        self._reconnect_delay = 3
        self._audio_chunk_queue = queue.Queue()
        self._audio_processing_active = True
        self._start_audio_processing_thread()
        
        self._setup_signals()
    
    def _setup_signals(self):
        """Connect signals to EventBus"""
        self._token_received.connect(
            lambda token: self._event_bus.emit(Event(EventType.AI_TOKEN_RECEIVED, str(token)))
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
            lambda error: self._event_bus.emit(Event(EventType.AI_ERROR_OCCURRED, str(error)))
        )
        self._recognition_result.connect(
            lambda text: self._event_bus.emit(Event(EventType.USER_TEXT_SUBMITTED, str(text)))
        )
        self._recognition_error.connect(
            lambda error: self._event_bus.emit(Event(EventType.AI_ERROR_OCCURRED, str(error)))
        )
        self._connection_lost.connect(
            lambda svc: self._event_bus.emit(Event(EventType.AI_ERROR_OCCURRED, f"Connection lost: {svc}"))
        )
        self._send_audio_chunk_signal.connect(self._process_audio_chunk)
    
    def _start_audio_processing_thread(self):
        """Start a thread to handle audio chunks safely"""
        def process_audio_chunks():
            while self._audio_processing_active:
                try:
                    chunk = self._audio_chunk_queue.get(timeout=0.1)
                    if chunk is None:  
                        break
                    self._send_audio_chunk_signal.emit(chunk)
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"Error in audio processing thread: {e}")
        
        self._audio_thread = threading.Thread(target=process_audio_chunks, daemon=True)
        self._audio_thread.start()
    
    def _process_audio_chunk(self, data: bytes):
        """Process audio chunk in the main thread"""
        try:
            if self.recognition_ws and self.recognition_ws.sock and self.recognition_ws.sock.connected:
                self.recognition_ws.send(data, opcode=websocket.ABNF.OPCODE_BINARY)
        except Exception as e:
            logger.error(f"Error sending audio: {e}")

    def initialize(self) -> None:
        """Connect to WebSocket"""
        self._connect_agent_ws()
        self._connect_recognition_ws()
    
    def _connect_agent_ws(self) -> None:
        """Connect to agent"""
        ws_url = self.base_url.replace("http://", "ws://") + "/ws/agent"
        
        def run():
            while self._should_reconnect:
                try:
                    self.agent_ws = websocket.WebSocketApp(
                        ws_url,
                        on_open=self._on_agent_open,
                        on_message=self._on_agent_message,
                        on_error=self._on_agent_error,
                        on_close=self._on_agent_close
                    )
                    self.agent_ws.run_forever(ping_interval=80, ping_timeout=60)
                except Exception as e:
                    logger.error(f"Agent connection error: {e}")
                
                if self._should_reconnect:
                    import time
                    time.sleep(self._reconnect_delay)
        
        threading.Thread(target=run, daemon=True).start()
    
    def _connect_recognition_ws(self) -> None:
        """Connect to recognition service"""
        ws_url = self.base_url.replace("http://", "ws://") + "/ws/recognition"
        
        def run():
            while self._should_reconnect:
                try:
                    self.recognition_ws = websocket.WebSocketApp(
                        ws_url,
                        on_open=self._on_recognition_open,
                        on_message=self._on_recognition_message,
                        on_error=self._on_recognition_error,
                        on_close=self._on_recognition_close
                    )
                    self.recognition_ws.run_forever(ping_interval=10, ping_timeout=5)
                except Exception as e:
                    logger.error(f"Recognition connection error: {e}")
                
                if self._should_reconnect:
                    import time
                    time.sleep(self._reconnect_delay)
        
        threading.Thread(target=run, daemon=True).start()
    
    def send_message(self, text: str) -> None:
        """Send text message"""
        if self.agent_ws and self.agent_ws.sock and self.agent_ws.sock.connected:
            try:
                self.agent_ws.send(json.dumps({
                    "type": "user_text",
                    "prompt": text
                }))
            except Exception as e:
                logger.error(f"Error sending message: {e}")
    
    def start_recording(self, sample_rate: int = 16000) -> None:
        """Start voice recording"""
        if self._recorder:
            self.stop_recording()
        
        if not self.recognition_ws or not self.recognition_ws.sock or not self.recognition_ws.sock.connected:
            logger.warning("Recognition WS not connected")
            return
        try:
            self.recognition_ws.send(json.dumps({
                "type": "recognize_start",
                "sample_rate": sample_rate
            }))
        except Exception as e:
            logger.error(f"Error sending start: {e}")
            return
        self._recorder = AudioRecorder(sample_rate)
        self._recorder.audio_chunk.connect(self._enqueue_audio_chunk)
        self._recorder.error_occurred.connect(self._on_recorder_error)
        self._recorder.finished.connect(self._on_recorder_finished)
        self._recorder.start()
        
        logger.info("Started recording")
    
    def _enqueue_audio_chunk(self, data: bytes):
        """Enqueue audio chunk for processing in a thread-safe manner"""
        try:
            self._audio_chunk_queue.put_nowait(data)
        except queue.Full:
            logger.warning("Audio chunk queue is full, dropping chunk")

    def _on_recorder_error(self, error: str):
        """Recorder error"""
        logger.error(f"Recorder error: {error}")
        self._recognition_error.emit(error)
    
    def _on_recorder_finished(self):
        """Recorder finished"""
        logger.info("Recorder finished")
        self._recorder = None
    
    def stop_recording(self) -> None:
        """Stop recording"""
        logger.info("Stopping recording...")
        
        if self._recorder:
            self._recorder.stop()
            self._recorder = None
        try:
            if self.recognition_ws and self.recognition_ws.sock and self.recognition_ws.sock.connected:
                self.recognition_ws.send(json.dumps({"type": "recognize_final"}))
        except Exception as e:
            logger.error(f"Error sending final: {e}")
    def _on_agent_open(self, ws) -> None:
        logger.info("Agent WS connected")
    
    def _on_agent_message(self, ws, message) -> None:
        """Handle agent messages"""
        if isinstance(message, bytes):
            return
        
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            
            if msg_type == "token":
                token = data.get("content", "")
                if token:
                    self._token_received.emit(str(token))
            
            elif msg_type == "tool_call":
                self._tool_call_started.emit()

            elif msg_type == "tool_call_complete":
                self._tool_call_completed.emit()
            
            elif msg_type == "complete":
                self._generation_completed.emit()
            
            elif msg_type == "error":
                error_msg = data.get("message", "Unknown error")
                self._generation_error.emit(str(error_msg))
                
        except Exception as e:
            logger.error(f"Agent message error: {e}")
    
    def _on_agent_error(self, ws, error) -> None:
        logger.error(f"Agent WS error: {error}")
    
    def _on_agent_close(self, ws, code, reason) -> None:
        logger.warning(f"Agent WS closed: {code}")
        self._connection_lost.emit("agent")
    
    def _on_recognition_open(self, ws) -> None:
        logger.info("Recognition WS connected")
    
    def _on_recognition_message(self, ws, message) -> None:
        """Handle recognition results"""
        if isinstance(message, bytes):
            return
        
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            
            if msg_type == "complete":
                content = data.get("content", "")
                if isinstance(content, dict):
                    text = content.get("final_text", "")
                elif isinstance(content, str):
                    text = content
                else:
                    text = str(content)
                if text:
                    self._recognition_result.emit(str(text))
            
            elif msg_type == "start":
                logger.info("Recognition started on server")
            
            elif msg_type == "error":
                error_msg = data.get("message", "Recognition error")
                self._recognition_error.emit(str(error_msg))
                
        except Exception as e:
            logger.error(f"Recognition message error: {e}")
    
    def _on_recognition_error(self, ws, error) -> None:
        logger.error(f"Recognition WS error: {error}")
    
    def _on_recognition_close(self, ws, code, reason) -> None:
        logger.warning(f"Recognition WS closed: {code}")
        self.stop_recording()
        self._connection_lost.emit("recognition")
    
    def cleanup(self) -> None:
        """Clean up resources"""
        logger.info("Cleaning up ApiService")
        self._should_reconnect = False
        self._audio_processing_active = False

        self._audio_chunk_queue.put(None)  
        if hasattr(self, '_audio_thread') and self._audio_thread.is_alive():
            self._audio_thread.join(timeout=2) 

        self.stop_recording()

        try:
            if self.agent_ws:
                self.agent_ws.close()
        except:
            pass
        
        try:
            if self.recognition_ws:
                self.recognition_ws.close()
        except:
            pass