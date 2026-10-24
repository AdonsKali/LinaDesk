from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from src.core.application.ports.command_bus import Command


@dataclass
class LoadSettingsCommand(Command):
    """Load settings command"""
    pass


@dataclass
class UpdateSettingsCommand(Command):
    """Update settings command"""
    field: str
    value: Any


@dataclass
class GetPluginListCommand(Command):
    """Get list of plugins command"""
    pass


@dataclass
class TogglePluginCommand(Command):
    """ON/OF plugin"""
    plugin_name: str
    enabled: bool


@dataclass
class SetToolPermissionsCommand(Command):
    tool_name: str
    permissions: list[str]


@dataclass
class ResolveToolPermissionCommand(Command):
    request_id: str
    allowed: bool
    remember: bool = False
    
    
@dataclass
class ToggleEconomyCommand(Command):
    """ON/OF economy mode"""
    pass
