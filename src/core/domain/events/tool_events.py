from dataclasses import dataclass
from typing import Any, Optional, Dict
from src.core.domain.events.base import DomainEvent


@dataclass
class ToolPermissionRequested(DomainEvent):
    request_id: str
    tool_name: str
    plugin_name: str
    user_id: str
    permissions: list[str]


@dataclass
class ToolPermissionRequestClosed(DomainEvent):
    request_id: str


@dataclass
class BackgroundJobFinished(DomainEvent):
    job_id: str
    tool_name: str
    user_id: str
    status: str
    result: Optional[str] = None
    error: Optional[str] = None


@dataclass
class ToolExecution(DomainEvent):
    """Event: The tool in process"""
    tool_name: str
    parameters: Dict[str, Any] | None = None
    
    def __post_init__(self):
        if not self.tool_name:
            raise ValueError("tool_name not must empty")

@dataclass
class ToolExecuted(DomainEvent):
    """
    Event: tool (plugin) executed.
    """
    tool_name: str
    result: Any
    parameters: Dict[str, Any] | None = None
    success: bool = True  # Set a default value
    error_message: Optional[str] = None
    execution_time_ms: Optional[float] = None
    
    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}
