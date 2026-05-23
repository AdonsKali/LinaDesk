from contextlib import asynccontextmanager
import uvicorn
import sys
from fastapi import FastAPI
from utils.logger import logger
from argparse import ArgumentParser
parser = ArgumentParser()
logger.setup(app_name="client", 
             log_dir="logs", 
             debug= True if "--debug" in sys.argv else False,
             clear_on_start=True)
log = logger.get(__name__)
from backend.presentation.server import create_app
from backend.infrastructure.config import Config
from backend.infrastructure.di.container import Container
from backend.infrastructure.tools.plugins.windows import *


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    log.info("Starting Lina AI Server...")

    config = Config()
    container = Container()
    container.config.from_pydantic(config)
    container.init_resources()
    
    log.info("Initializing LLM service...")
    container.inference() 
    
    log.info("Initializing ASR service...")
    container.recognizer()  

    log.info("Initializing Tool Manager...")
    container.tool_manager()
    
    log.info("Initializing RAG service...")
    container.rag_service()
    
    app.state.container = container
    
    log.info("Lina AI Server started successfully")
    yield
    
    log.info("Shutting down Lina AI Server...")
    container.shutdown_resources()
    log.info("Lina AI Server stopped")


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