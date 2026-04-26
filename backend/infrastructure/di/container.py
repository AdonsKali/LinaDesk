from dependency_injector import containers, providers
from backend.core.agent.agent import Agent
from backend.infrastructure.services import LlamaCppInference
from backend.infrastructure.services import VoskRecognizer
from backend.infrastructure.services import RAGService
from backend.application.agent_controller import AgentController
from backend.application.asr_controller import ASRController
from backend.application.tool_manager import ToolManager



class Container(containers.DeclarativeContainer):
    """DI контейнер с интерфейсами для всех сервисов"""
    
    wiring_config = containers.WiringConfiguration(
        modules=[
            "backend.presentation.server",
            "backend.presentation.websocket.agent_ws",
            "backend.presentation.websocket.asr_ws"
        ]
    )
    
    config = providers.Configuration()
    tool_manager = providers.Singleton(ToolManager)
    
    rag_service = providers.Singleton(
        RAGService,
        model_name=config.rag_model_path,
    )
    
    agent = providers.Factory(Agent,
        yaml_config="chibi.yaml"
    )
    
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
        rag_service=rag_service,
        enable_rag=True
    )
    
    asr_controller = providers.Factory(
        ASRController,
        recognizer=recognizer
    )