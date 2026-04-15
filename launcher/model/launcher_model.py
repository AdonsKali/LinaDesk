from typing import Optional
from dataclasses import dataclass


@dataclass
class LauncherModel:
    on_gpu:int = 0
    on_debug:int = 0
    on_log:int = 0
    on_eco:int = 0
    
    language = 'ru'
    user: str = 'User'
    microphone: Optional[str] = None
    camera: Optional[str] = None
    languages = ['ru', 'en', 'zh']

    server_pid: int = 0
    client_pid: int = 0

