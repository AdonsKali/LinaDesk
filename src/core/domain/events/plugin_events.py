from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from src.core.domain.events.base import DomainEvent


@dataclass
class PluginListRequested(DomainEvent):
    """
    Событие: запрошен список плагинов
    """
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PluginListReceived(DomainEvent):
    """
    Событие: получен список плагинов
    """
    plugins: List[Dict[str, Any]]
    timestamp: datetime = field(default_factory=datetime.now)
    


@dataclass
class PluginEnabled(DomainEvent):
    """
    Событие: плагин включен
    """
    plugin_name: str
    plugin_version: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        self.metadata = {"plugin": self.plugin_name}


@dataclass
class PluginDisabled(DomainEvent):
    """
    Событие: плагин выключен
    """
    plugin_name: str
    plugin_version: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        self.metadata = {"plugin": self.plugin_name}


@dataclass
class PluginToggled(DomainEvent):
    plugin_name: str
    enabled: bool
    plugin_version: str