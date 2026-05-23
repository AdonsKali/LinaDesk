from typing import Optional
from dataclasses import dataclass, field
from subprocess import Popen
from pathlib import Path
import configparser
from utils.logger import logger


@dataclass
class LauncherModel:
    on_gpu: bool = False
    on_debug: bool = False
    on_log: bool = False
    on_eco: bool = False
    
    language: str = 'ru'
    user: str = 'User'
    microphone: Optional[str] = None
    camera: Optional[str] = None
    languages: list = field(default_factory=lambda: ['ru', 'en', 'zh'])

    server_pid: int = 0
    client_pid: int = 0
    
    _config_path: Path = field(default=Path("launcher/launcher.ini"), repr=False, init=False)
    _parser: configparser.ConfigParser = field(default_factory=configparser.ConfigParser, repr=False, init=False)
    
    def load_from_file(self, config_path: Optional[Path] = None) -> None:
        """Загрузить настройки из файла"""
        if config_path:
            self._config_path = config_path
        
        if not self._config_path.exists():
            logger.info(f"Config file not found, using defaults: {self._config_path}")
            self.save_to_file()
            return
        
        try:
            self._parser.read(self._config_path, encoding='utf-8')
            
            self.on_gpu = self._parser.getboolean('CHECK BOX', 'on_gpu', fallback=False)
            self.on_debug = self._parser.getboolean('CHECK BOX', 'on_debug', fallback=False)
            self.on_log = self._parser.getboolean('CHECK BOX', 'on_log', fallback=False)
            self.on_eco = self._parser.getboolean('CHECK BOX', 'on_eco', fallback=False)
        
            self.user = self._parser.get('INPUTS', 'user', fallback='User')
            self.microphone = self._parser.get('INPUTS', 'microphone', fallback='undefined')
            self.camera = self._parser.get('INPUTS', 'camera', fallback='undefined')
            
            loaded_lang = self._parser.get('LANGUAGE', 'language', fallback='ru')
            self.language = loaded_lang if loaded_lang in self.languages else 'ru'
            
            self.server_pid = self._parser.getint('PID', 'server', fallback=0)
            self.client_pid = self._parser.getint('PID', 'client', fallback=0)
            
            logger.info(f"Config loaded from {self._config_path}")
            logger.debug(f"Debug mode from config: {self.on_debug}")
            
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
    
    def save_to_file(self) -> None:
        """Сохранить текущие настройки в файл"""
        try:
            for section in self._parser.sections():
                self._parser.remove_section(section)
            
            self._parser['CHECK BOX'] = {
                'on_gpu': str(self.on_gpu),
                'on_debug': str(self.on_debug),
                'on_log': str(self.on_log),
                'on_eco': str(self.on_eco)
            }
            
            self._parser['INPUTS'] = {
                'user': self.user,
                'microphone': self.microphone or 'undefined',
                'camera': self.camera or 'undefined'
            }
            
            # Сохраняем LANGUAGE
            self._parser['LANGUAGE'] = {
                'language': self.language
            }
            
            self._parser['PID'] = {
                'server': str(self.server_pid),
                'client': str(self.client_pid)
            }
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self._config_path, 'w', encoding='utf-8') as f:
                self._parser.write(f)
            
            logger.debug(f"Config saved to {self._config_path}")
            
        except Exception as e:
            logger.error(f"Failed to save config: {e}")


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