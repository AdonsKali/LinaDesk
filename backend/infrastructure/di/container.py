from dependency_injector import containers, providers

from backend.core import agent
from backend.core.agent.agent import Agent
from backend.infrastructure.services import LlamaCppInference, VoskRecognizer
from backend.infrastructure.tools.manager import ToolManager
from backend.application.agent_controller import AgentController
from backend.application.asr_controller import ASRController
from backend.infrastructure.services.RAG.rag_service import RAGService
from backend.application.agent_factory import AgentFactory
import os


class Container(containers.DeclarativeContainer):
    """Упрощенный DI контейнер"""
    
    wiring_config = containers.WiringConfiguration(
        modules=[
            "backend.presentation.server",
            "backend.presentation.websocket.agent_ws",
            "backend.presentation.websocket.asr_ws"
        ]
    )
    
    config = providers.Configuration()
    
    # Define path for RAG index files
    rag_index_path = f"backend/infrastructure/data/rag_index.faiss"
    
    tool_manager = providers.Singleton(ToolManager)
    # rag_service = providers.Singleton(
    #     RAGService,
    #     model_name=config.rag_model_path,
    #     index_path=rag_index_path
    # )
    agent_factory = providers.Factory(
        AgentFactory,
        tool_manager=tool_manager
    )
    agent = providers.Factory(Agent)
    
    inference = providers.Singleton(
        LlamaCppInference,
        model_path=config.llm_model_path,
        n_ctx=config.llm_context_size,
        n_threads=config.llm_threads,
        n_gpu_layers=config.llm_gpu_layers
    )
    
    recognizer = providers.Singleton(
        VoskRecognizer,
        model_path=config.asr_model_path
    )
    
    agent_controller = providers.Factory(
        AgentController,
        inference=inference,
        tool_manager=tool_manager,
        agent=agent,
        # rag_service=rag_service,
        enable_rag=True
    )
    
    asr_controller = providers.Factory(
        ASRController,
        recognizer=recognizer
    )