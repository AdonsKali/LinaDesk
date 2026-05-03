from fastapi import WebSocket
from typing import Dict, Optional, Any
import json
from utils.logger import get_logger

log = get_logger(__name__)


class BaseWebSocketHandler:
    """Базовый WebSocket хендлер с поддержкой нескольких клиентов"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str) -> bool:
        """Подключение клиента"""
        try:
            await websocket.accept()
            self.active_connections[client_id] = websocket
            log.info(f"Client {client_id} connected")
            return True
        except Exception as e:
            log.error(f"Connection error: {e}")
            return False
    
    async def disconnect(self, client_id: str):
        """Отключение клиента"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            log.info(f"Client {client_id} disconnected")
    
    async def send_json(self, client_id: str, data: dict):
        """Отправка JSON"""
        if client_id in self.active_connections:
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