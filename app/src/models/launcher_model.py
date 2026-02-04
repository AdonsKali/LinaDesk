from typing import Optional
from dataclasses import dataclass
from enum import Enum

@dataclass
class LauncherModel:
    """Модель данных лаунчера с автоматической валидацией"""
    on_gpu:int = 0
    on_debug:int = 0
    on_log:int = 0
    on_eco:int = 0
    
    language = 'ru'
    user: str = 'user'
    microphone: Optional[str] = None
    camera: Optional[str] = None

