import sys
import logging
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QTranslator
from core import Event, EventType,EventBus
from core.handlers.events_handler import EventHandler
from services.animation_service import AnimationService
from services.api_service import APIClient
from viewmodel.chibi_viewmodel import ChibiViewModel
from viewmodel.chat_viewmodel import ChatViewModel
from viewmodel.bubble_viewmodel import BubbleViewModel
from view.chibi_widget import ChibiWidget
from view.chat_widget import ChatWidget
from view.bubble_widget import BubbleWidget

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChibiApp:
    """Главное приложение"""
    
    def __init__(self):
        
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        self.translator = QTranslator(self.app)
        self.translator.load("/client/assets/language")
        
        # Шина событий
        self.event_bus = EventBus()
        
        # Сервисы
        self.animation_service = AnimationService()
        self.api_client = APIClient()
        
        # Обработчик событий
        self.handler = EventHandler(self.event_bus)
        self.handler.set_services(self.animation_service, self.api_client)
        
        # Подключаемся к серверу
        self.api_client.connect()
        
        # ViewModels
        self.chibi_vm = ChibiViewModel(self.event_bus)
        self.chat_vm = ChatViewModel(self.event_bus)
        self.bubble_vm = BubbleViewModel(self.event_bus)
        
        # Виджеты
        self.chibi_widget = ChibiWidget(self.chibi_vm, self.animation_service)
        self.chat_widget = ChatWidget(self.chat_vm)
        self.bubble_widget = BubbleWidget(self.bubble_vm)
        
        # Позиционирование
        self._position_widgets()
        
        # Подключение сигналов
        self.chibi_widget.position_changed.connect(self._on_chibi_moved)
        
        # Предзагрузка анимаций
        self._preload_animations()
        
        # Показываем начальный UI (через QTimer, чтобы не было рекурсии)
        QTimer.singleShot(100, self._show_initial_ui)
        
    
    def _position_widgets(self):
        """Позиционирование виджетов"""
        screen = self.app.primaryScreen()
        if screen:
            screen_geo = screen.geometry()
            x = (screen_geo.width() - 160) // 2
            y = (screen_geo.height() - 200) // 2
        else:
            x, y = 100, 100
        
        self.chibi_widget.move(x, y)
        self.chat_widget.move(x + 20, y + 200)
        self.bubble_widget.move(x + 250, y - 220)
        
    
    def _preload_animations(self):
        """Предзагрузка анимаций"""
        animations = ['idle', 'talk', 'think', 'process']
        self.animation_service.preload(animations)
    
    def _show_initial_ui(self):
        self.event_bus.emit(Event(EventType.UI_SHOW_CHAT))
        
    
    def _on_chibi_moved(self, pos):
        """Чиби переместился"""
        self.bubble_widget.move(pos.x() + 100, pos.y() - 120)
        self.bubble_widget.set_character_pos(pos)
        self.chat_widget.move(pos.x() + 20, pos.y() + 200)
    
    def run(self):
        """Запуск приложения"""
        self.chibi_widget.show()
        self.chibi_widget.raise_()
        
        logger.info("Starting Qt event loop...")
        return self.app.exec()


if __name__ == "__main__":
    app = ChibiApp()
    sys.exit(app.run())