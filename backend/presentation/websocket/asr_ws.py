from fastapi import WebSocket, WebSocketDisconnect
import uuid
from typing import Dict, Callable
import json

from .base_ws import BaseWebSocketHandler
from backend.application.asr_controller import ASRController
from logger import log


class ASRWebSocketHandler(BaseWebSocketHandler):
    """WebSocket хендлер для ASR"""
    
    def __init__(self):
        super().__init__()
        self.controllers: Dict[str, ASRController] = {}
    
    async def handle_connection(
        self, 
        websocket: WebSocket, 
        controller_factory: Callable[[], ASRController] 
    ):
        client_id = str(uuid.uuid4())
        
        if not await self.connect(websocket, client_id):
            return
        
        controller = controller_factory()
        self.controllers[client_id] = controller
        
        try:
            await self._message_loop(client_id, controller)
        except WebSocketDisconnect:
            await self._cleanup(client_id)
        except Exception as e:
            log(f"Error: {e}", 'error', __name__)
            await self._cleanup(client_id)
    
    async def _message_loop(self, client_id: str, controller: ASRController):
        """Цикл обработки сообщений - обработка любого типа сообщений"""
        while True:
            connection = self.active_connections.get(client_id)
            if not connection:
                break
                    
            try:
                message = await connection.receive()
                if message['type'] == 'websocket.receive':
                    if 'bytes' in message:
                        audio = message['bytes']
                        if audio:
                            result = controller.handle_audio_chunk(audio) 
                            if result:
                                await self.send_json(client_id, {"type": result.type, "content": result.content})
                    elif 'text' in message:
                        try:
                            data = json.loads(message['text'])
                            if data:
                                msg_type = data.get("type")
                                
                                if msg_type == "recognize_start":
                                    result = controller.handle_recognize_start(data) 
                                    if result:
                                        await self.send_json(client_id, {"type": result.type, "content": result.content})
                                
                                elif msg_type == "recognize_final":
                                    result = controller.handle_recognize_end()
                                    if result:
                                        await self.send_json(client_id, {"type": result.type, "content": result.content})
                                        
                        except json.JSONDecodeError as e:
                            log(f"Error decoding JSON: {e}", 'error', __name__)
            
            except WebSocketDisconnect:
                await self._cleanup(client_id)
                break  
            except Exception as e:
                if "disconnect message has been received" in str(e):
                    await self._cleanup(client_id)
                    break
                log(f"Error processing message: {e}", 'error', __name__)
                continue
    
    async def _cleanup(self, client_id: str):
        """Очистка ресурсов"""
        if client_id in self.controllers:
            del self.controllers[client_id]
        await self.disconnect(client_id)