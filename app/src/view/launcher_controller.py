from ..models import LauncherModel
from PySide6.QtCore import QObject, Signal
from typing import Dict
import configparser
config = configparser.ConfigParser()


class ViewLauncher(QObject):

    enable_logging_changed = Signal(int)
    debug_mode_changed = Signal(int)
    use_gpu_changed = Signal(int)
    use_economy_changed = Signal(int)

    update_user = Signal(str)
    update_language_ru = Signal(int)
    update_language_en = Signal(int)
    update_microphone = Signal(str)
    update_camera = Signal(int)


    def __init__(self) -> None:
        super().__init__()
        self.model = LauncherModel()
        self.config = configparser.ConfigParser()
        self.load_all()


    def gpu(self, state: bool):
        state = int(state)
        if self.model.on_gpu != state:
            self.model.on_gpu = state
            self.use_gpu_changed.emit(state)

    def get_gpu(self):
        return self.model.on_gpu

    def log(self, state: bool):
        state = int(state)
        if self.model.on_log != state:
            self.model.on_log = state
            self.enable_logging_changed.emit(state)

    def get_log(self):
        return self.model.on_log

    def debug(self, state: bool):
        state = int(state)
        if self.model.on_debug != state:
            self.model.on_debug = state
            self.debug_mode_changed.emit(state)

    def get_debug(self):
        return self.model.on_debug

    def eco(self, state: bool):
        state = int(state)
        if self.model.on_eco != state:
            self.model.on_eco = state
            self.use_economy_changed.emit(state)

    def get_eco(self):
        return self.model.on_eco
    
    def change_user(self, name: str):
        self.model.user = name

    def get_user(self):
        return self.model.user
    
    def change_language_ru(self):
        self.model.language = 'ru'
        self.update_language_ru.emit(True)

    def change_language_en(self):
        self.model.language = 'en'
        self.update_language_en.emit(True)

    def get_language(self):
        return self.model.language

    def save_all(self):
        self.config.read('launcher.ini')
        self.config['CHECK BOX']['on_gpu'] = str(self.model.on_gpu)
        self.config['CHECK BOX']['on_debug'] = str(self.model.on_debug)
        self.config['CHECK BOX']['on_log'] = str(self.model.on_log)
        self.config['CHECK BOX']['on_eco'] = str(self.model.on_eco)
        self.config['LANGUAGE']['language'] = str(self.model.language)
        with open('launcher.ini', 'w') as f:
            self.config.write(f)


    def load_all(self):
        self.config.read('launcher.ini')
        self.model.on_gpu = int(self.config['CHECK BOX']['on_gpu'])
        self.model.on_debug = int(self.config['CHECK BOX']['on_debug'])
        self.model.on_log = int(self.config['CHECK BOX']['on_log'])
        self.model.on_eco= int(self.config['CHECK BOX']['on_economy'])
        self.model.language= str(self.config['LANGUAGE']['language'])
            

