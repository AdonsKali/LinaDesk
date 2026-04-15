import subprocess
from typing import Optional
from logger import log
from ..model import LauncherModel
from PySide6.QtCore import QObject, Signal, QTranslator
from PySide6.QtWidgets import QApplication
from launcher.server_manager import ServerManager
from launcher.client_manager import ClientManager
import configparser

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
    client_pid_changed = Signal(int)

    start_app = Signal()
    stop_app = Signal()
    server_pid_changed = Signal(int)

    save_all = Signal()
    kill_all = Signal()

    def __init__(self):
        super().__init__()
        self.model = LauncherModel()
        self.server_manager = ServerManager()
        self.client_manager = ClientManager()
        self.config = configparser.ConfigParser()
        self.client_process: Optional[subprocess.Popen] = None

        self.update_language.connect(self._apply_language)
        self.start_app.connect(self._start_app)
        self.start_server.connect(self._start_server)
        self.stop_app.connect(self._stop_app)
        self.stop_server.connect(self._stop_server)
        self.save_all.connect(self._save_all)
        self.kill_all.connect(self._force_kill)

        # self.server_pid_changed.connect(self.check_server_process)
        # self.client_pid_changed.connect(self.check_client_process)

        self.server_manager.server_error.connect(lambda msg: log(f"Server error: {msg}", "error", __name__))

        self.translator = QTranslator(QApplication.instance())

        self.launcher_ini = 'launcher/launcher.ini'
        self.load_all()

    def gpu(self, state: bool):
        state = int(state)  
        if self.model.on_gpu != state:
            self.model.on_gpu = state
            self.use_gpu_changed.emit(state)  

    def get_gpu(self):
        return bool(self.model.on_gpu)  

    def log(self, state: bool):
        if self.model.on_log != int(state):  
            self.model.on_log = int(state)
            self.enable_logging_changed.emit(state)  

    def get_log(self):
        return bool(self.model.on_log)

    def debug(self, state: bool):
        if self.model.on_debug != int(state):
            self.model.on_debug = int(state)
            self.debug_mode_changed.emit(state)

    def get_debug(self):
        return bool(self.model.on_debug)

    def eco(self, state: bool):
        if self.model.on_eco != int(state):
            self.model.on_eco = int(state)
            self.use_economy_changed.emit(state)

    def get_eco(self):
        return bool(self.model.on_eco)
    
    def change_user(self, name: str):
        self.model.user = name
        self.update_user.emit(name) 

    def get_user(self):
        return self.model.user
    
    def change_language(self, language_code: str):
        if language_code in self.model.languages and self.model.language != language_code:
            self.model.language = language_code
            self.update_language.emit(language_code)
        self._apply_language()

    def get_language(self):
        return self.model.language
    
    def load_language(self):
        return self.config.get('LANGUAGE', 'language', fallback='ru')


    def _save_all(self):
        if 'CHECK BOX' not in self.config:
            self.config['CHECK BOX'] = {}
        if 'LANGUAGE' not in self.config:
            self.config['LANGUAGE'] = {}
            
        self.config['CHECK BOX']['on_gpu'] = str(self.model.on_gpu)
        self.config['CHECK BOX']['on_debug'] = str(self.model.on_debug)
        self.config['CHECK BOX']['on_log'] = str(self.model.on_log)
        self.config['CHECK BOX']['on_eco'] = str(self.model.on_eco)
        self.config['INPUTS']['user'] = str(self.model.user)
        self.config['INPUTS']['microphone'] = str(self.model.microphone)
        self.config['INPUTS']['camera'] = str(self.model.camera)
        self.config['LANGUAGE']['language'] = str(self.model.language)
        
        with open(self.launcher_ini, 'w') as f:
            self.config.write(f)

    def load_all(self):
        self.config.read(self.launcher_ini)
        
        self.model.on_gpu = int(self.config.get('CHECK BOX', 'on_gpu', fallback='0'))
        self.model.on_debug = int(self.config.get('CHECK BOX', 'on_debug', fallback='0'))
        self.model.on_log = int(self.config.get('CHECK BOX', 'on_log', fallback='0'))
        self.model.on_eco = int(self.config.get('CHECK BOX', 'on_eco', fallback='0'))
        self.model.user = str(self.config.get('INPUTS', 'user', fallback='user'))
        self.model.microphone = str(self.config.get('INPUTS', 'microphone', fallback='undefine'))
        self.model.camera = str(self.config.get('INPUTS', 'camera', fallback='undefine'))
        loaded_lang = self.config.get('LANGUAGE', 'language', fallback='ru')
        self.model.server_pid =  self.config.getint('PID', 'server', fallback=0)
        self.model.client_pid = self.config.getint('PID', 'client', fallback=0)
        self.model.language = loaded_lang if loaded_lang in self.model.languages else 'ru'


    def _apply_language(self):
        app = QApplication.instance()
        app.removeTranslator(self.translator)
        file_path = f'launcher/model/languages/{self.model.language}/launcher.qm'
        if self.translator.load(file_path) and self.model.language != 'en':
            app.installTranslator(self.translator)
        elif self.model.language != 'en':
            log(f"Language file not found: {file_path}", "warning", __name__)
        self.language_changed.emit()


    def _start_server(self):
        try:
            self.server_manager.start()
        except Exception as e:
            log(f"Error starting server: {e}", "error", __name__)

    
    def _start_app(self):
        self.client_manager.start(self.model.language, bool(self.model.on_debug))

    def _stop_app(self):
        self.client_manager.stop()

    def _stop_server(self):
        try:
            self.server_manager.stop()
        except Exception as e:
            log(f"Error stopping server: {e}", "error", __name__)

    def is_app_running(self):
        return (
            self.client_process is not None and 
            self.client_process.poll() is None
        )

    def is_server_running(self):
        return self.server_manager.is_running()
    

    def _force_kill(self):
        self.client_manager.force_kill()
        self.server_manager.stop()
        self.model.server_pid = 0
        self.model.client_pid = 0
        self.save_all.emit()
        QApplication.exit(1)


    # def check_server_process(self, pid):
    #     self.config['PID']['server'] = str(self.model.server_pid)
    #     self.model.server_pid =  self.config.getint('PID', 'server', fallback=0)
    #     if pid != 0:
    #         self.model.server_pid = pid
    #     self.config['PID']['server'] = str(self.model.server_pid)

    # def check_client_process(self, pid):
    #     if self.model.client_pid == 0:
    #         self.model.client_pid = pid
    #         self.config['PID']['client'] = str(self.model.client_pid)
    #         self.model.client_pid = self.config.getint('PID', 'client', fallback=0)
    #     else:
    #         ...