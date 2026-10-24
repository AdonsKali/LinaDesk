import os
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer, QThread, QCoreApplication
from .views.chibi_view import ChibiView
from .views.bubble_view import BubbleView
from .views.chat_view import ChatView
from .views.statuses_view import StatusesView
from src.core.utils.logger import logger
from argparse import ArgumentParser
parser = ArgumentParser()
from .app_coordinator import AppCoordinator
from src.core.domain.events.desktop_events import DesktopActionRequested
from src.core.domain.events.emotion_events import EmotionChanged
from .core.events import Event
from .core.event_types import EventType
import gc

logger = logger.get(__name__)

class ChibiApp:
    """Главное приложение"""
    def __init__(self, command_bus, event_bus):
        self._command_bus = command_bus
        self._event_bus = event_bus
        self._is_initialized = False
        self._is_shutting_down = False
        
        self.coordinator = None
        self.chibi_view = None
        self.bubble_view = None
        self.chat_view = None
        self.statuses_view = None
        self._connections = []
        
        self._initialize()
        self._event_bus.subscribe(DesktopActionRequested, self._on_desktop_action)
        self._event_bus.subscribe(EmotionChanged, self._on_emotion)

    async def _on_desktop_action(self, event):
        if self._is_shutting_down:
            return
        if event.action == "move":
            self.chibi_view.walk(event.value)
        elif event.action == "animation":
            self.coordinator.event_bus.emit(Event(EventType.CHIBI_ANIMATION_CHANGED, event.value))
            QTimer.singleShot(3500, self._finish_autonomous_animation)

    def _finish_autonomous_animation(self):
        if not self._is_shutting_down and not self.coordinator.chat_vm.is_processing:
            self.coordinator.event_bus.emit(Event(EventType.CHIBI_ANIMATION_CHANGED, "idle"))

    async def _on_emotion(self, event):
        if not self._is_shutting_down:
            self.chibi_view.set_emotion(event.new_emotion.type.value)
    
    def _initialize(self):
        """Инициализация приложения"""
        if self._is_initialized:
            return
            
        logger.info("=" * 60)
        logger.info("Initializing ChibiApp...")
        logger.info("=" * 60)
        
        # Проверяем существующие виджеты
        app = QApplication.instance()
        if app:
            widgets_before = len(app.topLevelWidgets())
            logger.info(f"Top level widgets before: {widgets_before}")
        
        self.coordinator = AppCoordinator(self._command_bus, self._event_bus)
        
        self.chibi_view = ChibiView(
            self.coordinator.chibi_vm,
            self.coordinator.animation_service
        )
        self.bubble_view = BubbleView(self.coordinator.bubble_vm)
        self.chat_view = ChatView(self.coordinator.chat_vm)
        self.statuses_view = StatusesView(self.coordinator.statuses_vm)
        
        logger.info("Setting up view connections...")
        self._setup_view_connections()
        
        logger.info("Setting up PositionService...")
        self._setup_position_service()

        logger.info("Initializing services...")
        self.coordinator.initialize()
        self._show_initial_ui()
        
        self._is_initialized = True
        
        # Проверяем виджеты после создания
        if app:
            widgets_after = len(app.topLevelWidgets())
            logger.info(f"Top level widgets after: {widgets_after}")
        
        logger.info("=" * 60)
        logger.info("ChibiApp initialized successfully")
        logger.info("=" * 60)
    
    def _setup_view_connections(self):
        """Настройка связей View с ViewModels."""
        self._disconnect_all()

        # Сохраняем пары (signal, slot) для отписки
        connections = [
            (
                self.chibi_view.position_changed,
                lambda x, y: self.coordinator.position_service.on_chibi_moved(x, y),
            ),
            (
                self.coordinator.bubble_vm.position_coordinates_changed,
                self.bubble_view.move,
            ),
            (
                self.chibi_view.position_changed,
                lambda x, y: self.bubble_view.set_character_pos(self.chibi_view.pos()),
            ),
            (
                self.coordinator.chat_vm.position_changed,
                self.chat_view.move,
            ),
            (
                self.coordinator.statuses_vm.position_changed,
                self.statuses_view.move,
            ),
            (
                self.chibi_view.double_clicked,
                self._on_chibi_activated,
            ),
        ]

        self._connections = connections
        for signal, slot in connections:
            signal.connect(slot)
    
    def _disconnect_all(self):
        """Отключение всех сигналов."""
        for signal, slot in self._connections:
            try:
                signal.disconnect(slot)
            except (RuntimeError, TypeError):
                # Slot уже отключён или сигнал удалён — игнорируем
                pass
        self._connections.clear()
    
    def _setup_position_service(self):
        """Настройка сервиса позиционирования"""
        if not self.coordinator:
            return
            
        screen = QApplication.instance().primaryScreen()
        if screen:
            screen_geo = screen.geometry()
            self.coordinator.position_service.set_screen_size(
                screen_geo.width(), 
                screen_geo.height()
            )
        
        if self.chibi_view and self.bubble_view and self.chat_view:
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
        if self._is_shutting_down:
            return
        if self.chat_view:
            self.chat_view.show()
            self.chat_view.raise_()
        if self.bubble_view:
            self.bubble_view.show()
            self.bubble_view.raise_()
        if self.chibi_view:
            self.chibi_view.raise_()
    
    def _show_initial_ui(self):
        """Начальный показ UI - только чиби"""
        if not self.chibi_view:
            return
            
        screen = QApplication.instance().primaryScreen()
        if screen:
            screen_geo = screen.geometry()
            chibi_x = screen_geo.x() + (screen_geo.width() - self.chibi_view.width()) // 2
            chibi_y = screen_geo.y() + (screen_geo.height() - self.chibi_view.height()) // 2
            
            self.chibi_view.move(chibi_x, chibi_y)
            if self.coordinator and self.coordinator.position_service:
                self.coordinator.position_service.on_chibi_moved(chibi_x, chibi_y)
        
        self.chibi_view.show()
        self.chibi_view.raise_()
    
    async def aclose(self):
        if self.coordinator:
            await self.coordinator.api_service.aclose()
        self.shutdown()

    def shutdown(self):
        """Полное завершение работы"""
        if self._is_shutting_down:
            return
        
        self._is_shutting_down = True
        self._event_bus.unsubscribe(DesktopActionRequested, self._on_desktop_action)
        self._event_bus.unsubscribe(EmotionChanged, self._on_emotion)
        logger.info("=" * 60)
        logger.info("Shutting down ChibiApp...")
        logger.info("=" * 60)
        
        # 1. Отключаем все сигналы
        self._disconnect_all()

        # QLabel does not own its QMovie. Detach native pointers before either
        # the view or the animation service schedules its objects for deletion.
        if self.chibi_view:
            self.chibi_view.setMovie(None)
        if self.coordinator and self.coordinator.animation_service:
            for movie in self.coordinator.animation_service._cache.values():
                movie.stop()
        
        # 2. Закрываем все View
        views = [
            ('bubble_view', self.bubble_view),
            ('chat_view', self.chat_view),
            ('chibi_view', self.chibi_view),
            ('statuses_view', self.statuses_view)
        ]
        
        for name, view in views:
            if view:
                try:
                    view.close()
                    view.hide()
                    view.setParent(None)
                    view.deleteLater()
                except Exception as e:
                    logger.error(f"Error deleting {name}: {e}")
                setattr(self, name, None)
        
        # 3. Очищаем Coordinator
        if self.coordinator:
            try:
                self.coordinator.cleanup()
                self.coordinator.setParent(None)
                self.coordinator.deleteLater()
            except Exception as e:
                logger.error(f"Error cleaning coordinator: {e}")
            self.coordinator = None
        
        self._is_initialized = False
        
        logger.info("=" * 60)
        logger.info("ChibiApp shutdown complete")
        logger.info("=" * 60)
    
    def __del__(self):
        """Деструктор для дополнительной очистки"""
        if not self._is_shutting_down:
            try:
                self.shutdown()
            except:
                pass
