from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime
from src.core.domain.events.base import DomainEvent


@dataclass
class SettingsLoaded(DomainEvent):
    """
    Event: settings loaded
    Occurs upon system startup or when loading saved settings.
    """
    settings: Dict[str, Any]
    source: str = "file"  # file, default, user
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        self.aggregate_id = "settings"
        self.metadata = {"source": self.source}


@dataclass
class SettingsChanged(DomainEvent):
    """
    Event: settings changed
    Occurs when any parameter is changed
    """
    old_settings: Dict[str, Any]
    new_settings: Dict[str, Any]
    changed_fields: List[str]
    changed_by: str = "user"  # user, system, plugin
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        self.aggregate_id = "settings"
        self.metadata = {
            "fields": self.changed_fields,
            "changed_by": self.changed_by
        }


@dataclass
class SettingsReset(DomainEvent):
    """
    Event: settings reset to default values
    """
    default_settings: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        self.aggregate_id = "settings"
        self.metadata = {"event": "settings_reset"}