from dataclasses import dataclass
from typing import Dict, Any
from src.core.application.ports.command_bus import Command


@dataclass
class StartSystemCommand(Command):
    """Команда запуска системы"""
    pass


@dataclass
class StopSystemCommand(Command):
    """Команда остановки системы"""
    reason: str = "user_request"
    
    
@dataclass
class ExitApplicationCommand(Command):
    """Команда выхода из приложения"""
    pass