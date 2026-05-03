from fastapi import WebSocket, WebSocketDisconnect
import uuid
from typing import Dict, Callable
from backend.core.schemas.client_schema import ClientComplete, ClientToolCall, ClientToken, ClientError
from .base_ws import BaseWebSocketHandler
from backend.application.agent_controller import AgentController
from utils.logger import get_logger

log = get_logger(__name__)


class AgentWebSocketHandler(BaseWebSocketHandler):
    """WebSocket хендлер для агента"""
    
    def __init__(self):
        super().__init__()
        self.controllers: Dict[str, AgentController] = {}
    
    async def handle_connection(
        self, 
        websocket: WebSocket, 
        controller_factory: Callable[[], AgentController]
    ):
        """
        Обработка WebSocket соединения
        
        Args:
            websocket: WebSocket соединение
            controller_factory: фабрика для создания контроллеров
        """
        client_id = str(uuid.uuid4())
        
        if not await self.connect(websocket, client_id):
            return
        
        try:
            controller = controller_factory()
            self.controllers[client_id] = controller
            
            await self._message_loop(client_id, controller)
        except WebSocketDisconnect:
            await self._cleanup(client_id)
        except Exception as e:
            log.error(f"Error in agent WebSocket: {e}")
            await self._cleanup(client_id)
    
    async def _message_loop(self, client_id: str, controller: AgentController):
        """Основной цикл обработки сообщений"""
        while True:
            data = await self.receive_json(client_id)
            if not data:
                continue
            
            msg_type = data.get("type")
            content = data.get("prompt", "")
            
            if msg_type == "user_text":
                async for data in controller.response(content):
                    if isinstance(data, ClientToken):
                        await self.send_json(client_id, {"type": data.type, "content": data.content})
                    elif isinstance(data, ClientToolCall):
                        await self.send_json(client_id, {"type": data.type, "content": data.data})
                    elif isinstance(data, ClientComplete) or isinstance(data, ClientError):
                        await self.send_json(client_id, {"type": data.type})
            
            
            elif msg_type == "reset":
                controller.reset()
                await self.send_json(client_id, {"type": "reset"})
    
    async def _cleanup(self, client_id: str):
        """Очистка ресурсов"""
        if client_id in self.controllers:
            self.controllers[client_id].reset()
            del self.controllers[client_id]
        await self.disconnect(client_id)