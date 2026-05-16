from typing import Optional
from dataclasses import dataclass
from subprocess import Popen


@dataclass
class LauncherModel:
    on_gpu: bool = False
    on_debug: bool = False
    on_log: bool = False
    on_eco: bool = False
    
    language = 'ru'
    user: str = 'User'
    microphone: Optional[str] = None
    camera: Optional[str] = None
    languages = ['ru', 'en', 'zh']

    server_pid: int = 0
    client_pid: int = 0


@dataclass
class ProcessInfo:
    """Information about a managed process"""
    process: Optional[Popen]
    pid: int = -1
    identifier: str = ""
    
    def is_running(self) -> bool:
        if not self.process:
            return False
        return self.process.poll() is None


