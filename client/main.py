import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from client.views.chibi_view import ChibiView
from client.views.bubble_view import BubbleView
from client.views.chat_view import ChatView
from utils.logger import logger
from argparse import ArgumentParser
parser = ArgumentParser()
logger.setup(app_name="client", 
             log_dir="logs", 
             debug= True if "--debug" in sys.argv else False,
             clear_on_start=True)
from app_coordinator import AppCoordinator


log = logger.get(__name__)

class ChibiApp:
    """Главное приложение"""
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        
        self.coordinator = AppCoordinator()

        self.chibi_view = ChibiView(
            self.coordinator.chibi_vm,
            self.coordinator.animation_service
        )
        self.bubble_view = BubbleView(self.coordinator.bubble_vm)
        self.chat_view = ChatView(self.coordinator.chat_vm)
        
        log.info("Setting up view connections...")
        self._setup_view_connections()
        
        log.info("Setting up PositionService...")
        self._setup_position_service()

        log.info("Initializing services...")
        self.coordinator.initialize()
        QTimer.singleShot(100, self._show_initial_ui)
    
    def _setup_view_connections(self):
        """Настройка связей View с ViewModels"""

        self.chibi_view.position_changed.connect(
            lambda x, y: self.coordinator.position_service.on_chibi_moved(x, y)
        )
        
        self.coordinator.bubble_vm.position_coordinates_changed.connect(
            self.bubble_view.move
        )
        self.chibi_view.position_changed.connect(
            lambda x, y: self.bubble_view.set_character_pos(self.chibi_view.pos())
        )
        
        self.coordinator.chat_vm.position_changed.connect(
            self.chat_view.move
        )
        
        self.chibi_view.double_clicked.connect(self._on_chibi_activated)
    
    def _setup_position_service(self):
        """Настройка сервиса позиционирования"""
        screen = self.app.primaryScreen()
        if screen:
            screen_geo = screen.geometry()
            self.coordinator.position_service.set_screen_size(
                screen_geo.width(), 
                screen_geo.height()
            )
        
        self.coordinator.position_service.set_widget_sizes(
            chibi_w=self.chibi_view.width(),
            chibi_h=self.chibi_view.height(),
            bubble_w=self.bubble_view.width(),
            bubble_h=self.bubble_view.height(),
            chat_w=self.chat_view.sizeHint().width(),
            chat_h=self.chat_view.height()
        )
    
    def _on_chibi_activated(self):
        """Активация чиби (двойной клик)"""
        self.chat_view.show()
        self.chat_view.raise_()
        self.bubble_view.show()
        self.bubble_view.raise_()
        self.chibi_view.raise_()
    
    def _show_initial_ui(self):
        """Начальный показ UI - только чиби"""
        screen = self.app.primaryScreen()
        if screen:
            screen_geo = screen.geometry()
            chibi_x = (screen_geo.width() - self.chibi_view.width()) // 2
            chibi_y = (screen_geo.height() - self.chibi_view.height()) // 2
            
            self.chibi_view.move(chibi_x, chibi_y)
            self.coordinator.position_service.on_chibi_moved(chibi_x, chibi_y)
        
        self.chibi_view.show()
        self.chibi_view.raise_()
    
    def run(self):
        """Запуск приложения"""
        return self.app.exec()

def app():
    app = ChibiApp()
    return app.run()

if __name__ == "__main__":
    sys.exit(app())