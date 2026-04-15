from fastapi import WebSocket
from typing import Dict, Optional, Any
import json
from backend.core.schemas.client_schema import MessageClientSchema
from logger import log


class BaseWebSocketHandler:
    """Базовый WebSocket хендлер с поддержкой нескольких клиентов"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str) -> bool:
        """Подключение клиента"""
        try:
            await websocket.accept()
            self.active_connections[client_id] = websocket
            log(f"Client {client_id} connected", 'info', __name__)
            return True
        except Exception as e:
            log(f"Connection error: {e}", 'error', __name__)
            return False
    
    async def disconnect(self, client_id: str):
        """Отключение клиента"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            log(f"Client {client_id} disconnected", 'info', __name__)
    
    async def send_json(self, client_id: str, data: dict):
        """Отправка JSON"""
        if client_id in self.active_connections:
            log(data, 'info', __name__)
            await self.active_connections[client_id].send_json(data)
    
    async def receive_json(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Получение JSON"""
        if client_id in self.active_connections:
            try:
                text = await self.active_connections[client_id].receive_text()
                return json.loads(text)
            except json.JSONDecodeError:
                return None
        return None
    
    async def receive_bytes(self, client_id: str) -> Optional[bytes]:
        """Получение бинарных данных"""
        if client_id in self.active_connections:
            return await self.active_connections[client_id].receive_bytes()
        return None