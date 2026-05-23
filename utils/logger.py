import logging
import logging.handlers
from pathlib import Path
from typing import Optional

COLORS = {
    'DEBUG': '\033[94m',     # синий
    'INFO': '\033[92m',      # зелёный
    'WARNING': '\033[93m',   # жёлтый
    'ERROR': '\033[91m',     # красный
    'CRITICAL': '\033[95m',  # фиолетовый
    'RESET': '\033[0m'
}

class ColoredFormatter(logging.Formatter):
    def format(self, record):
        levelname = record.levelname
        if levelname in COLORS:
            record.levelname = f"{COLORS[levelname]}{levelname:7s}{COLORS['RESET']}"
        return super().format(record)

class Logger:
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def setup(
        self,
        app_name: str = "lina_app",
        log_dir: str = "./logs",
        debug: bool = False,
        clear_on_start: bool = False,
        log_to_file: bool = True,
        log_to_console: bool = True,
        max_file_size_mb: int = 10,
        backup_count: int = 5
    ):
        """Настройка логгера"""
        if self._initialized:
            return
            
        self.app_name = app_name
        log_dir_path = Path(log_dir)
        log_dir_path.mkdir(parents=True, exist_ok=True)
        
        self.logger = logging.getLogger(app_name)
        self.logger.setLevel(logging.DEBUG if debug else logging.INFO)
        
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        console_formatter = ColoredFormatter(
            '%(levelname)s [%(asctime)s] [%(name)s] %(message)s',
            datefmt='%H:%M:%S'
        )
        
        if log_to_file:
            file_handler = logging.handlers.RotatingFileHandler(
                log_dir_path / f"{app_name}.log",
                maxBytes=max_file_size_mb * 1024 * 1024,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
            
            error_handler = logging.handlers.RotatingFileHandler(
                log_dir_path / f"{app_name}_error.log",
                maxBytes=max_file_size_mb * 1024 * 1024,
                backupCount=backup_count,
                encoding='utf-8'
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(file_formatter)
            self.logger.addHandler(error_handler)
        
        if log_to_console:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)
        
        if clear_on_start and log_to_file:
            for log_file in log_dir_path.glob(f"{app_name}*.log*"):
                try:
                    log_file.unlink()
                except PermissionError:
                    try:
                        with open(log_file, 'w', encoding='utf-8') as f:
                            f.write('') 
                    except Exception as e:
                        self.warning(f"Failed to clear {log_file}: {e}")
                except Exception as e:
                    self.warning(f"Failed to delete {log_file}: {e}")
        
        self._initialized = True
        self.info(f"Initialization logger (debug = {'on' if debug else 'off'})")
    def update_debug_mode(self, debug: bool):
        """Обновить debug режим на лету"""
        if not self._initialized:
            return
        
        new_level = logging.DEBUG if debug else logging.INFO
        if self.logger.level != new_level:
            self.logger.setLevel(new_level)
            self.info(f"Debug mode {'enabled' if debug else 'disabled'}")
    def get(self, name: Optional[str] = None) -> logging.Logger:
        """Получить логгер"""
        if name:
            return self.logger.getChild(name)
        return self.logger
    
    def debug(self, msg, *args, **kwargs):
        if self._initialized:
            self.logger.debug(msg, *args, **kwargs)
    
    def info(self, msg, *args, **kwargs):
        if self._initialized:
            self.logger.info(msg, *args, **kwargs)
    
    def warning(self, msg, *args, **kwargs):
        if self._initialized:
            self.logger.warning(msg, *args, **kwargs)
    
    def error(self, msg, *args, **kwargs):
        if self._initialized:
            self.logger.error(msg, *args, **kwargs)
    
    def critical(self, msg, *args, **kwargs):
        if self._initialized:
            self.logger.critical(msg, *args, **kwargs)

logger = Logger()