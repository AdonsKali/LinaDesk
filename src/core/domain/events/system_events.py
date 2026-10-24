from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime
from src.core.domain.events.base import DomainEvent


@dataclass(kw_only=True)
class SystemStartRequested(DomainEvent):
    """
    Event: system startup request
    """
    settings: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        self.aggregate_id = "system"
        self.metadata = {"event": "start_requested"}


@dataclass(kw_only=True)
class SystemStarted(DomainEvent):
    """
    Event: System started
    """
    boot_time_ms: float
    components: List[str]
    settings: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        self.aggregate_id = "system"
        self.metadata = {"boot_time_ms": self.boot_time_ms}


@dataclass(kw_only=True)
class SystemStopRequested(DomainEvent):
    """
    Event: system shutdown request
    """
    reason: str = "user_request"
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        self.aggregate_id = "system"
        self.metadata = {"reason": self.reason}


@dataclass(kw_only=True)
class SystemStopped(DomainEvent):
    """
    Event: System stopped
    """
    uptime_seconds: float
    reason: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        self.aggregate_id = "system"
        self.metadata = {"uptime_seconds": self.uptime_seconds}


@dataclass(kw_only=True)
class SystemRestartRequested(DomainEvent):
    """
    Event: system restart request
    """
    reason: str = "user_request"
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        self.aggregate_id = "system"
        self.metadata = {"reason": self.reason}


@dataclass(kw_only=True)
class SystemError(DomainEvent):
    """
    Event: system error
    """
    error: str
    component: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        self.aggregate_id = "system"
        self.metadata = {
            "error": self.error,
            "component": self.component
        }