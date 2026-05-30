from pydantic_settings import BaseSettings
from paths import MODELS, VOSK_MODEL
from pydantic import Field


class Config(BaseSettings):
    llm_model_path: str = Field(default=f"{MODELS}/model3.gguf", alias="LLM_MODEL_PATH")
    llm_context_size: int = Field(default=4096, alias="LLM_CONTEXT_SIZE")
    llm_threads: int = Field(default=6, alias="LLM_THREADS")
    llm_gpu_layers: int | str = Field(default=18, alias="LLM_GPU_LAYERS")
    llm_clip_model_path: str | None = Field(default=None, alias="LLM_CLIP_MODEL_PATH")
    
    asr_model_path: str = Field(default=str(VOSK_MODEL), alias="ASR_MODEL_PATH")
    
    rag_model_path: str = Field(default="all-MiniLM-L6-v2", alias="RAG_MODEL_PATH")
    
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    reload: bool = Field(default=False, alias="RELOAD")

    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    
    agent_ymal_file: str = Field(default="chibi.yaml", alias="AGENT_YAML_FILE")
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "forbid" 