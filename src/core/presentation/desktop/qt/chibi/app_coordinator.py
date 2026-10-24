from PySide6.QtCore import QObject, QTimer
from .core.event_bus import EventBus
from .core.events import Event
from .core.event_types import EventType
from .services.animation_service import AnimationService
from .services.api_service import ApiService
from .services.position_service import PositionService
from .viewmodels.chibi_viewmodel import ChibiViewModel
from .viewmodels.bubble_viewmodel import BubbleViewModel
from .viewmodels.chat_viewmodel import ChatViewModel
from .viewmodels.statuses_viewmodel import StatusesViewModel
from .models.chibi_model import ChibiState, AnimationType
from src.core.utils.logger import logger
import gc

logger = logger.get(__name__)


class AppCoordinator(QObject):
    """Координатор приложения"""
    
    def __init__(self, command_bus, system_event_bus):
        super().__init__()
        
        self._command_bus = command_bus
        self._system_event_bus = system_event_bus
        self._ai_streaming = False  
        self._first_token = False
        self._is_cleaned = False
        
        self.event_bus = EventBus()
        
        self.animation_service = AnimationService(self.event_bus)
        self.api_service = ApiService(self.event_bus, command_bus, system_event_bus)
        self.position_service = PositionService(self.event_bus)

        self.statuses_vm = StatusesViewModel(self.event_bus)
        self.chibi_vm = ChibiViewModel(self.event_bus)
        self.bubble_vm = BubbleViewModel(self.event_bus)
        self.chat_vm = ChatViewModel(self.event_bus)

        self._handlers = []
        self._setup_handlers()
    
    def _setup_handlers(self) -> None:
        """Настройка обработчиков событий"""
        subscriptions = [
            (EventType.USER_TEXT_SUBMITTED, self._on_user_text),
            (EventType.AI_TOKEN_RECEIVED, self._on_ai_token),
            (EventType.AI_RESPONSE_COMPLETED, self._on_ai_completed),
            (EventType.AI_RESPONSE_STARTED, self._on_ai_response_started),
            (EventType.AI_ERROR_OCCURRED, self._on_ai_error),
            (EventType.AI_TOOL_CALL_STARTED, self._on_tool_call_started),
            (EventType.AI_TOOL_CALL_COMPLETED, self._on_tool_call_completed),
            (EventType.USER_CHIBI_CLICKED, self._on_chibi_clicked),
            (EventType.USER_CHIBI_DRAGGED, self._on_chibi_dragged),
            (EventType.USER_VOICE_STARTED, self._on_voice_started),
            (EventType.USER_VOICE_STOPPED, self._on_voice_stopped),
        ]
        
        for event_type, handler in subscriptions:
            self.event_bus.subscribe(event_type, handler)
            self._handlers.append((event_type, handler))
    
    def _on_user_text(self, event: Event) -> None:
        if self._is_cleaned:
            return
        self._ai_streaming = False
        self._first_token = True
        self.event_bus.emit(Event(EventType.CHIBI_STATE_CHANGED, ChibiState.THINKING.name))
        self.event_bus.emit(Event(EventType.CHIBI_ANIMATION_CHANGED, AnimationType.THINK.value))
        self.event_bus.emit(Event(EventType.CHAT_PROCESSING_CHANGED, True))

    def _on_ai_token(self, event: Event) -> None:
        if self._is_cleaned:
            return
        token = event.data
        if self._first_token:
            self._first_token = False
            self._ai_streaming = True
            self.event_bus.emit(Event(EventType.CHIBI_STATE_CHANGED, ChibiState.TALKING.name))
            self.event_bus.emit(Event(EventType.CHIBI_ANIMATION_CHANGED, AnimationType.TALK.value))
            self.bubble_vm.show("")
        self.bubble_vm.append_token(token)
        
    def _on_ai_response_started(self, event: Event) -> None:
        if self._is_cleaned:
            return
        self._first_token = True
        self.event_bus.emit(Event(EventType.CHAT_PROCESSING_CHANGED, True))
        self.event_bus.emit(Event(EventType.CHIBI_ANIMATION_CHANGED, AnimationType.THINK.value))

    def _on_ai_completed(self, event: Event) -> None:
        """AI завершил генерацию"""
        if self._is_cleaned:
            return
            
        self._ai_streaming = False
        self._first_token = False
        
        self.event_bus.emit(Event(EventType.CHIBI_STATE_CHANGED, ChibiState.IDLE.name))
        self.event_bus.emit(Event(EventType.CHIBI_ANIMATION_CHANGED, AnimationType.IDLE.value))
        self.event_bus.emit(Event(EventType.CHAT_PROCESSING_CHANGED, False))
        

    def _on_ai_error(self, event: Event) -> None:
        """Ошибка AI"""
        if self._is_cleaned:
            return
            
        self._ai_streaming = False
        self._first_token = False
        error_msg = event.data or "Unknown error"
        self.bubble_vm.show(f"{error_msg}")
        
        self.event_bus.emit(Event(EventType.CHIBI_STATE_CHANGED, ChibiState.IDLE.name))
        self.event_bus.emit(Event(EventType.CHIBI_ANIMATION_CHANGED, AnimationType.IDLE.value))
        self.event_bus.emit(Event(EventType.CHAT_PROCESSING_CHANGED, False))
    
    def _on_tool_call_started(self, event: Event) -> None:
        """Начало вызова инструмента"""
        if self._is_cleaned:
            return
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        self.event_bus.emit(Event(EventType.CHIBI_STATE_CHANGED, ChibiState.PROCESSING.name))
        self.event_bus.emit(Event(EventType.CHIBI_ANIMATION_CHANGED, AnimationType.PROCESS.value))
    
    def _on_tool_call_completed(self, event: Event) -> None:
        """Завершение вызова инструмента"""
        if self._is_cleaned:
            return
        self.event_bus.emit(Event(EventType.CHIBI_STATE_CHANGED, ChibiState.TALKING.name))
        self.event_bus.emit(Event(EventType.CHIBI_ANIMATION_CHANGED, AnimationType.TALK.value))
    
    def _on_chibi_clicked(self, event: Event) -> None:
        if self._is_cleaned:
            return
        logger.info("Clicked")
        self.api_service.activity_callback()
        # НЕ вызываем bubble_vm.show() — BubbleViewModel сам обрабатывает
        self.chat_vm.show()
    
    def _on_chibi_dragged(self, event: Event) -> None:
        """Перетаскивание чиби"""
        if self._is_cleaned:
            return
        x, y = event.data
        self.api_service.activity_callback()
        self.position_service.on_chibi_moved(x, y)
    
    def _on_voice_started(self, event: Event) -> None:
        """Начало голосового ввода"""
        if self._is_cleaned:
            return
        self.event_bus.emit(Event(EventType.CHIBI_STATE_CHANGED, ChibiState.LISTENING.name))
        self.event_bus.emit(Event(EventType.CHIBI_ANIMATION_CHANGED, AnimationType.IDLE.value))

    def _on_voice_stopped(self, event: Event) -> None:
        """Остановка голосового ввода"""
        if self._is_cleaned:
            return
    
    def initialize(self) -> None:
        """Инициализация всех компонентов"""
        if self._is_cleaned:
            return
        self.animation_service.initialize()
        self.api_service.initialize()
    
    def cleanup(self) -> None:
        """Полная очистка ресурсов"""
        if self._is_cleaned:
            return
        
        self._is_cleaned = True
        logger.info("=" * 60)
        logger.info("Cleaning up AppCoordinator...")
        logger.info("=" * 60)
        
        # 1. Отписываемся от всех событий
        for event_type, handler in self._handlers:
            try:
                self.event_bus.unsubscribe(event_type, handler)
            except Exception as e:
                logger.error(f"Error unsubscribing from {event_type}: {e}")
        self._handlers.clear()
        
        # 2. Очищаем все ViewModels
        viewmodels = [
            ('statuses_vm', self.statuses_vm),
            ('chibi_vm', self.chibi_vm),
            ('bubble_vm', self.bubble_vm),
            ('chat_vm', self.chat_vm)
        ]
        
        for name, vm in viewmodels:
            if vm and hasattr(vm, 'cleanup'):
                try:
                    vm.cleanup()
                except Exception as e:
                    logger.error(f"Error cleaning {name}: {e}")
                setattr(self, name, None)
        
        # 3. Очищаем сервисы
        if self.animation_service:
            try:
                self.animation_service.cleanup()
                self.animation_service.setParent(None)
                self.animation_service.deleteLater()
            except Exception as e:
                logger.error(f"Error cleaning animation_service: {e}")
            self.animation_service = None
        
        if self.api_service:
            try:
                if hasattr(self.api_service, 'cleanup'):
                    self.api_service.cleanup()
                self.api_service.setParent(None)
                self.api_service.deleteLater()
            except Exception as e:
                logger.error(f"Error cleaning api_service: {e}")
            self.api_service = None
        
        if self.position_service:
            try:
                self.position_service.setParent(None)
                self.position_service.deleteLater()
            except Exception as e:
                logger.error(f"Error cleaning position_service: {e}")
            self.position_service = None
        
        # 4. Очищаем EventBus
        if self.event_bus:
            try:
                if hasattr(self.event_bus, '_subscribers'):
                    self.event_bus._subscribers.clear()
                if hasattr(self.event_bus, '_handlers'):
                    self.event_bus._handlers.clear()
            except Exception as e:
                logger.error(f"Error clearing event_bus: {e}")
            self.event_bus = None
        
        # 5. Удаляем дочерние объекты
        for child in self.children():
            try:
                child.setParent(None)
                child.deleteLater()
            except:
                pass
        
        # 6. Очищаем ссылки
        self._command_bus = None
        self._system_event_bus = None
        
        # 7. Сборка мусора
        gc.collect()
        
        logger.info("=" * 60)
        logger.info("AppCoordinator cleaned up")
        logger.info("=" * 60)
