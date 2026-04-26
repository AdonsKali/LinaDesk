from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI
from backend.presentation.server import create_app
from backend.infrastructure.config import Config
from backend.infrastructure.di.container import Container
from backend.infrastructure.tools.plugins.windows import *
from logger import log


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    log("Starting Lina AI Server...", 'info', __name__)

    config = Config()
    container = Container()
    container.config.from_pydantic(config)
    container.init_resources()
    
    log("Initializing LLM service...", 'info', __name__)
    container.inference() 
    
    log("Initializing ASR service...", 'info', __name__)
    container.recognizer()  

    log("Initializing Tool Manager...", 'info', __name__)
    container.tool_manager()
    
    log("Initializing RAG service...", 'info', __name__)
    container.rag_service()
    
    app.state.container = container
    
    log("Lina AI Server started successfully", 'info', __name__)
    yield
    
    log("Shutting down Lina AI Server...", 'info', __name__)
    container.shutdown_resources()
    log("Lina AI Server stopped", 'info', __name__)


def create_application() -> FastAPI:
    """Фабрика для создания приложения"""
    app = create_app()
    app.router.lifespan_context = lifespan
    return app


if __name__ == "__main__":
    config = Config()
    uvicorn.run(
        "backend.run:create_application",
        host=config.host,
        port=config.port,
        reload=config.reload,
        factory=True
    )