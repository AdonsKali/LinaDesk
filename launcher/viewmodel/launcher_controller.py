from pathlib import Path
from ..model import LauncherModel
from PySide6.QtCore import QObject, Signal, QTranslator
from PySide6.QtWidgets import QApplication
from launcher.utils.process_manager import ProcessManager, ProcessType
from utils.logger import logger


class ViewLauncher(QObject):
    enable_logging_changed = Signal(bool)
    debug_mode_changed = Signal(bool)
    use_gpu_changed = Signal(bool)
    use_economy_changed = Signal(bool)
    language_changed = Signal()
    
    update_user = Signal(str)
    update_language = Signal(str)
    update_microphone = Signal(str)
    update_camera = Signal(int)
    
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
    
    client_pid_changed = Signal(int)
    server_pid_changed = Signal(int)
    
    quit_lina = Signal()
    save_all = Signal()
    
    def __init__(self, model: LauncherModel):
        super().__init__()
        
        self.model = model
        self.process_manager = ProcessManager()
        self.translator = QTranslator(QApplication.instance())
        self.log_ = logger.get(__name__)
        self._setup_connections()
        self._apply_language()
        self._sync_process_manager_settings()
        self._handle_existing_processes()
        self._emit_initial_states()
    
    def _emit_initial_states(self):
        """Отправить начальные состояния в UI"""
        self.use_gpu_changed.emit(self.model.on_gpu)
        self.debug_mode_changed.emit(self.model.on_debug)
        self.enable_logging_changed.emit(self.model.on_log)
        self.use_economy_changed.emit(self.model.on_eco)
        self.update_user.emit(self.model.user)
        self.server_pid_changed.emit(self.model.server_pid)
        self.client_pid_changed.emit(self.model.client_pid)
    
    def _setup_connections(self):
        """Setup all signal-slot connections"""
        self.process_manager.process_started.connect(self._on_process_started)
        self.process_manager.process_stopped.connect(self._on_process_stopped)
        self.process_manager.process_error.connect(self._on_process_error)
        
        self.update_language.connect(self._apply_language)
        self.start_app.connect(self._start_app)
        self.start_server.connect(self._start_server)
        self.stop_app.connect(self._stop_app)
        self.stop_server.connect(self._stop_server)
        self.save_all.connect(self._save_all)
        self.quit_lina.connect(self.quit_app)
        
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
            self._save_all()
            self.log_.debug(f"GPU mode: {state}")
    
    def get_gpu(self) -> bool:
        return self.model.on_gpu
    
    def log(self, state: bool) -> None:
        state = bool(state)
        if self.model.on_log != state:
            self.model.on_log = state
            self.enable_logging_changed.emit(state)
            self._save_all()
            self.log_.debug(f"Logging mode: {state}")
    
    def get_log(self) -> bool:
        return self.model.on_log
    
    def debug(self, state: bool) -> None:
        state = bool(state)
        if self.model.on_debug != state:
            self.model.on_debug = state
            self.debug_mode_changed.emit(state)
            self._sync_process_manager_settings()
            self._save_all()
            logger.update_debug_mode(state)
            self.log_.debug(f"Debug mode: {state}")
    
    def get_debug(self) -> bool:
        return self.model.on_debug
    
    def eco(self, state: bool) -> None:
        state = bool(state)
        if self.model.on_eco != state:
            self.model.on_eco = state
            self.use_economy_changed.emit(state)
            self._save_all()
            self.log_.debug(f"Economy mode: {state}")
    
    def get_eco(self) -> bool:
        return self.model.on_eco
    
    def change_user(self, name: str) -> None:
        if self.model.user != name:
            self.model.user = name
            self.update_user.emit(name)
            self._save_all()
            self.log_.debug(f"User: {name}")
    
    def get_user(self) -> str:
        return self.model.user
    
    def change_language(self, language_code: str) -> None:
        if (language_code in self.model.languages and 
            self.model.language != language_code):
            self.model.language = language_code
            self.update_language.emit(language_code)
            self._apply_language()
            self._save_all()
            self.log_.debug(f"Language: {language_code}")
    
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
            self.log_.debug("Starting server...")
        except Exception as e:
            self.log_.error(f"Error starting server: {e}")
    
    def _start_app(self) -> None:
        """Start the client application"""
        try:
            self._sync_process_manager_settings()
            self.process_manager.start_client(self.model.language)
            self.log_.debug("Starting app...")
        except Exception as e:
            self.log_.error(f"Error starting client: {e}")
    
    def _stop_app(self) -> None:
        """Stop the client application"""
        try:
            self.process_manager.stop_client()
            self.log_.debug("Stopping app...")
        except Exception as e:
            self.log_.error(f"Error stopping app: {e}")
    
    def _stop_server(self) -> None:
        """Stop the server process"""
        try:
            self.process_manager.stop_server()
            self.log_.debug("Stopping server...")
        except Exception as e:
            self.log_.error(f"Error stopping server: {e}")
    
    def _on_process_pid_changed(self, proc_type: ProcessType, pid: int) -> None:
        """Handle process PID changes"""
        if proc_type == ProcessType.SERVER:
            self.model.server_pid = pid
            self.server_pid_changed.emit(pid)
        else:
            self.model.client_pid = pid
            self.client_pid_changed.emit(pid)
        self._save_all()
    
    def _on_process_started(self, proc_type: ProcessType):
        if proc_type == ProcessType.SERVER:
            self.server_started.emit()
            self.log_.info("Server started")
        else:
            self.client_started.emit()
            self.log_.info("Client started")
    
    def _on_process_stopped(self, proc_type: ProcessType):
        if proc_type == ProcessType.SERVER:
            self.server_stopped.emit()
            self.log_.info("Server stopped")
        else:
            self.client_stopped.emit()
            self.log_.info("Client stopped")
    
    def _on_process_error(self, proc_type: ProcessType, error_msg: str):
        if proc_type == ProcessType.SERVER:
            self.server_error.emit(error_msg)
        else:
            self.client_error.emit(error_msg)
        self.log_.error(f"{proc_type.value} error: {error_msg}")
    
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
            self.log_.debug(f"Language applied: {self.model.language}")
        else:
            self.log_.warning(f"Language file not found: {qm_file}")
        
        self.language_changed.emit()
    
    # ==================== Configuration Management ====================
    
    def _save_all(self) -> None:
        """Save all settings to configuration file"""
        self.model.save_to_file()
    
    # ==================== Process Cleanup ====================
    
    def _handle_existing_processes(self) -> None:
        """Check for existing processes from previous sessions."""
        orphaned_pids = {}
        
        if self.model.server_pid > 0:
            orphaned_pids['server'] = self.model.server_pid
            self.log_.info(f"Found orphaned server PID: {self.model.server_pid}")
        
        if self.model.client_pid > 0:
            orphaned_pids['client'] = self.model.client_pid
            self.log_.info(f"Found orphaned client PID: {self.model.client_pid}")
        
        if orphaned_pids:
            self.process_manager.cleanup_hanging_processes(orphaned_pids)
            self.model.server_pid = 0
            self.model.client_pid = 0
            self._save_all()
    
    # ==================== Application Lifecycle ====================
    
    def quit_app(self) -> None:
        """Properly shuts down the application and all managed processes."""
        import time
        
        self.log_.info("Shutting down launcher application...")
        
        try:
            time.sleep(0.5)
            self.process_manager.stop_all(force=False)
            
            self.model.server_pid = 0
            self.model.client_pid = 0
            self._save_all()
            
            self.log_.info("Application shutdown complete")
            QApplication.exit(0)
            
        except Exception as e:
            self.log_.error(f"Error during application shutdown: {e}")
            QApplication.exit(1)