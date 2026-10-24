from enum import Enum, auto


class Status(str, Enum):
    """Общие статусы операций."""
    OK = "ok"
    ERROR = "error"
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ErrorCode(str, Enum):
    """Коды ошибок."""
    # Общие
    UNKNOWN = "unknown"
    VALIDATION = "validation_error"
    NOT_FOUND = "not_found"
    PERMISSION = "permission_error"
    
    # LLM
    LLM_ERROR = "llm_error"
    LLM_TIMEOUT = "llm_timeout"
    LLM_RATE_LIMIT = "llm_rate_limit"
    
    # Память
    MEMORY_ERROR = "memory_error"
    MEMORY_FULL = "memory_full"
    
    # Система
    SYSTEM_ERROR = "system_error"
    CONFIG_ERROR = "config_error"