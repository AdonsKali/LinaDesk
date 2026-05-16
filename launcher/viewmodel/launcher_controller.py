from pathlib import Path
from ..model import LauncherModel
from PySide6.QtCore import QObject, Signal, QTranslator
from PySide6.QtWidgets import QApplication
from launcher.viewmodel.utils.process_manager import ProcessManager, ProcessType
import configparser
from utils.logger import get_logger

log = get_logger(__name__)


class ViewLauncher(QObject):
    # UI State Signals
    enable_logging_changed = Signal(bool)
    debug_mode_changed = Signal(bool)
    use_gpu_changed = Signal(bool)
    use_economy_changed = Signal(bool)
    language_changed = Signal()
    
    # User Input Signals
    update_user = Signal(str)
    update_language = Signal(str)
    update_microphone = Signal(str)
    update_camera = Signal(int)
    
    # Process Control Signals
    start_server = Signal()
    stop_server = Signal()
    start_app = Signal()
    stop_app = Signal()

    server_started = Signal()
    server_stopped = Signal()
    server_error = Signal(str)
    client_started = Signal()
    client_stopped = Signal()
    client_error = Signal(str)
    
    # Process Status Signals (for UI updates)
    client_pid_changed = Signal(int)
    server_pid_changed = Signal(int)
    
    # Application Control
    quit_lina = Signal()
    save_all = Signal()
    
    LAUNCHER_INI = Path('launcher/launcher.ini')
    
    def __init__(self):
        super().__init__()
        
        self.model = LauncherModel()
        self.process_manager = ProcessManager()
        self.config = configparser.ConfigParser()
        self.translator = QTranslator(QApplication.instance())
        
        self._setup_connections()
        self.load_all()
        self._apply_language()
        self._sync_process_manager_settings()
        self._handle_existing_processes()
    
    # ==================== Connection Setup ====================
    
    def _setup_connections(self):
        """Setup all signal-slot connections"""

        self.process_manager.process_started.connect(self._on_process_started)
        self.process_manager.process_stopped.connect(self._on_process_stopped)
        self.process_manager.process_error.connect(self._on_process_error)
        # UI to Handler connections
        self.update_language.connect(self._apply_language)
        self.start_app.connect(self._start_app)
        self.start_server.connect(self._start_server)
        self.stop_app.connect(self._stop_app)
        self.stop_server.connect(self._stop_server)
        self.save_all.connect(self._save_all)
        self.quit_lina.connect(self.quit_app)
        
        # Process Manager to Controller connections
        self.process_manager.process_pid_changed.connect(self._on_process_pid_changed)
        self.process_manager.process_error.connect(self._on_process_error)
        self.process_manager.process_started.connect(self._on_process_started)
        self.process_manager.process_stopped.connect(self._on_process_stopped)
    
    # ==================== Public Getters/Setters ====================
    
    def gpu(self, state: bool) -> None:
        state = bool(state)
        if self.model.on_gpu != state:
            self.model.on_gpu = state
            self.use_gpu_changed.emit(state)
    
    def get_gpu(self) -> bool:
        return bool(self.model.on_gpu)
    
    def log(self, state: bool) -> None:
        state = bool(state)
        if self.model.on_log != state:
            self.model.on_log = state
            self.enable_logging_changed.emit(state)
    
    def get_log(self) -> bool:
        return bool(self.model.on_log)
    
    def debug(self, state: bool) -> None:
        state = bool(state)
        if self.model.on_debug != state:
            self.model.on_debug = state
            self.debug_mode_changed.emit(state)
            self._sync_process_manager_settings()
    
    def get_debug(self) -> bool:
        return bool(self.model.on_debug)
    
    def eco(self, state: bool) -> None:
        state = bool(state)
        if self.model.on_eco != state:
            self.model.on_eco = state
            self.use_economy_changed.emit(state)
    
    def get_eco(self) -> bool:
        return bool(self.model.on_eco)
    
    def change_user(self, name: str) -> None:
        if self.model.user != name:
            self.model.user = name
            self.update_user.emit(name)
    
    def get_user(self) -> str:
        return self.model.user
    
    def change_language(self, language_code: str) -> None:
        if (language_code in self.model.languages and 
            self.model.language != language_code):
            self.model.language = language_code
            self.update_language.emit(language_code)
            self._apply_language()
    
    def get_language(self) -> str:
        return self.model.language
    
    # ==================== Process Status ====================
    
    def is_app_running(self) -> bool:
        return self.process_manager.is_running(ProcessType.CLIENT)
    
    def is_server_running(self) -> bool:
        return self.process_manager.is_running(ProcessType.SERVER)
    
    # ==================== Private Methods ====================
    
    def _sync_process_manager_settings(self) -> None:
        """Sync settings from model to process manager"""
        self.process_manager.debug_mode = bool(self.model.on_debug)
    
    def _start_server(self) -> None:
        """Start the server process"""
        try:
            self._sync_process_manager_settings()
            self.process_manager.start_server()
        except Exception as e:
            log.error(f"Error starting server: {e}")
    
    def _start_app(self) -> None:
        """Start the client application"""
        try:
            self._sync_process_manager_settings()
            self.process_manager.start_client(self.model.language)
        except Exception as e:
            log.error(f"Error starting client: {e}")
    
    def _stop_app(self) -> None:
        """Stop the client application"""
        try:
            self.process_manager.stop_client()
        except Exception as e:
            log.error(f"Error stopping app: {e}")
    
    def _stop_server(self) -> None:
        """Stop the server process"""
        try:
            self.process_manager.stop_server()
        except Exception as e:
            log.error(f"Error stopping server: {e}")
    
    def _on_process_pid_changed(self, proc_type: ProcessType, pid: int) -> None:
        """Handle process PID changes"""
        if proc_type == ProcessType.SERVER:
            self.model.server_pid = pid
            self.server_pid_changed.emit(pid)
        else:  # CLIENT
            self.model.client_pid = pid
            self.client_pid_changed.emit(pid)
        self._save_all()
    
    def _on_process_started(self, proc_type: ProcessType):
        if proc_type == ProcessType.SERVER:
            self.server_started.emit()
        else:
            self.client_started.emit()
    
    def _on_process_stopped(self, proc_type: ProcessType):
        if proc_type == ProcessType.SERVER:
            self.server_stopped.emit()
        else:
            self.client_stopped.emit()
    
    def _on_process_error(self, proc_type: ProcessType, error_msg: str):
        if proc_type == ProcessType.SERVER:
            self.server_error.emit(error_msg)
        else:
            self.client_error.emit(error_msg)
    
    def _apply_language(self) -> None:
        """Apply the selected language to the UI"""
        app = QApplication.instance()
        if not app:
            return
        app.removeTranslator(self.translator)
        if self.model.language == 'en':
            self.language_changed.emit()
            return
        
        qm_file = Path(f'launcher/model/languages/{self.model.language}/launcher.qm')
        
        if qm_file.exists() and self.translator.load(str(qm_file)):
            app.installTranslator(self.translator)
        else:
            log.warning(f"Language file not found: {qm_file}")
        
        self.language_changed.emit()
    
    # ==================== Configuration Management ====================
    
    def _save_all(self) -> None:
        """Save all settings to configuration file"""
        sections = ['CHECK BOX', 'LANGUAGE', 'PID', 'INPUTS']
        for section in sections:
            if section not in self.config:
                self.config[section] = {}
        
        self.config['CHECK BOX'].update({
            'on_gpu': str(self.model.on_gpu),
            'on_debug': str(self.model.on_debug),
            'on_log': str(self.model.on_log),
            'on_eco': str(self.model.on_eco)
        })

        self.config['INPUTS'].update({
            'user': str(self.model.user),
            'microphone': str(self.model.microphone),
            'camera': str(self.model.camera)
        })
        
        self.config['LANGUAGE']['language'] = str(self.model.language)
        self.config['PID']['server'] = str(self.model.server_pid)
        self.config['PID']['client'] = str(self.model.client_pid)
        try:
            with open(self.LAUNCHER_INI, 'w', encoding='utf-8') as f:
                self.config.write(f)
        except IOError as e:
            log.error(f"Failed to save configuration: {e}")
    
    def load_all(self) -> None:
        """Load all settings from configuration file"""
        if not self.LAUNCHER_INI.exists():
            log.info(f"Config file not found, using defaults: {self.LAUNCHER_INI}")
            self._apply_defaults()
            return
        
        try:
            self.config.read(self.LAUNCHER_INI, encoding='utf-8')
        except Exception as e:
            log.error(f"Failed to read configuration: {e}")
            self._apply_defaults()
            return
        
        # Load checkbox states
        self.model.on_gpu = self.config.getboolean('CHECK BOX', 'on_gpu', fallback=False)
        self.model.on_debug = self.config.getboolean('CHECK BOX', 'on_debug', fallback=False)
        self.model.on_log = self.config.getboolean('CHECK BOX', 'on_log', fallback=False)
        self.model.on_eco = self.config.getboolean('CHECK BOX', 'on_eco', fallback=False)
        
        # Load inputs
        self.model.user = self.config.get('INPUTS', 'user', fallback='user')
        self.model.microphone = self.config.get('INPUTS', 'microphone', fallback='undefined')
        self.model.camera = self.config.get('INPUTS', 'camera', fallback='undefined')
        
        # Load and validate language
        loaded_lang = self.config.get('LANGUAGE', 'language', fallback='ru')
        self.model.language = loaded_lang if loaded_lang in self.model.languages else 'ru'
        
        # Load PIDs
        self.model.server_pid = self.config.getint('PID', 'server', fallback=0)
        self.model.client_pid = self.config.getint('PID', 'client', fallback=0)
    
    def _apply_defaults(self) -> None:
        """Apply default configuration values"""
        self.model.on_gpu = False
        self.model.on_debug = False
        self.model.on_log = False
        self.model.on_eco = False
        self.model.user = 'user'
        self.model.microphone = 'undefined'
        self.model.camera = 'undefined'
        self.model.language = 'ru'
        self.model.server_pid = 0
        self.model.client_pid = 0

    
    
    # ==================== Process Cleanup ====================
    
    def _handle_existing_processes(self) -> None:
        """
        Check for existing processes from previous sessions.
        The improved ProcessManager handles this more gracefully.
        """
        orphaned_pids = {}
        
        if self.model.server_pid > 0:
            orphaned_pids['server'] = self.model.server_pid
            log.info(f"Found orphaned server PID: {self.model.server_pid}")
        
        if self.model.client_pid > 0:
            orphaned_pids['client'] = self.model.client_pid
            log.info(f"Found orphaned client PID: {self.model.client_pid}")
        
        if orphaned_pids:
            self.process_manager.cleanup_hanging_processes(orphaned_pids)
            # Reset PIDs after cleanup
            self.model.server_pid = 0
            self.model.client_pid = 0
            self._save_all()
    
    # ==================== Application Lifecycle ====================
    
    def quit_app(self) -> None:
        """
        Properly shuts down the application and all managed processes.
        Saves state before exit.
        """
        import time
        
        log.info("Shutting down launcher application...")
        
        try:
            time.sleep(0.5)

            self.process_manager.stop_all(force=False)
            
            self.model.server_pid = 0
            self.model.client_pid = 0
            self._save_all()
            
            log.info("Application shutdown complete")
            QApplication.exit(0)
            
        except Exception as e:
            log.error(f"Error during application shutdown: {e}")
            QApplication.exit(1)