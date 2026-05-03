from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI
from backend.presentation.server import create_app
from backend.infrastructure.config import Config
from backend.infrastructure.di.container import Container
from backend.infrastructure.tools.plugins.windows import *
from utils.logger import setup, get_logger

setup(app_name="backend", log_dir="logs", debug=False)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    logger.info("Starting Lina AI Server...")

    config = Config()
    container = Container()
    container.config.from_pydantic(config)
    container.init_resources()
    
    logger.info("Initializing LLM service...")
    container.inference() 
    
    logger.info("Initializing ASR service...")
    container.recognizer()  

    logger.info("Initializing Tool Manager...")
    container.tool_manager()
    
    logger.info("Initializing RAG service...")
    container.rag_service()
    
    app.state.container = container
    
    logger.info("Lina AI Server started successfully")
    yield
    
    logger.info("Shutting down Lina AI Server...")
    container.shutdown_resources()
    logger.info("Lina AI Server stopped")


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