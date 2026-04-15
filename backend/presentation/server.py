from fastapi import FastAPI, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware
from dependency_injector.wiring import inject, Provide
from backend.infrastructure.di.container import Container
from backend.presentation.websocket.agent_ws import AgentWebSocketHandler
from backend.presentation.websocket.asr_ws import ASRWebSocketHandler
from logger import log


def create_app() -> FastAPI:
    """Фабрика FastAPI приложения"""
    app = FastAPI(title="Lina AI", version="1.0.0")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    @app.websocket("/ws/agent")
    @inject
    async def agent_websocket(
        websocket: WebSocket,
        controller_factory = Depends(Provide[Container.agent_controller.provider])
    ):
        handler = AgentWebSocketHandler()
        await handler.handle_connection(websocket, controller_factory)
    
    @app.websocket("/ws/recognition")
    @inject
    async def asr_websocket(
        websocket: WebSocket,
        controller_factory = Depends(Provide[Container.asr_controller.provider])
    ):
        handler = ASRWebSocketHandler()
        await handler.handle_connection(websocket, controller_factory)
    
    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "Lina AI"}
    
    return app