
from PySide6.QtCore import QObject
from client.core.event_bus import EventBus
from client.core.events import Event
from client.core.event_types import EventType
from client.services.animation_service import AnimationService
from client.services.api_service import ApiService
from client.services.position_service import PositionService
from client.viewmodels.chibi_viewmodel import ChibiViewModel
from client.viewmodels.bubble_viewmodel import BubbleViewModel
from client.viewmodels.chat_viewmodel import ChatViewModel
from client.models.chibi_model import ChibiState, AnimationType
from utils.logger import get_logger

log = get_logger(__name__)


class AppCoordinator(QObject):
    """Координатор приложения"""
    
    def __init__(self):
        super().__init__()
        
        self._ai_streaming = False  
        self._first_token = False
        self.event_bus = EventBus()
        
        self.animation_service = AnimationService(self.event_bus)
        self.api_service = ApiService(self.event_bus)
        self.position_service = PositionService(self.event_bus)

        self.chibi_vm = ChibiViewModel(self.event_bus)
        self.bubble_vm = BubbleViewModel(self.event_bus)
        self.chat_vm = ChatViewModel(self.event_bus)

        self._setup_handlers()
    
    def _setup_handlers(self) -> None:
        """Настройка обработчиков событий"""
        self.event_bus.subscribe(EventType.USER_TEXT_SUBMITTED, self._on_user_text)
        self.event_bus.subscribe(EventType.AI_TOKEN_RECEIVED, self._on_ai_token)
        self.event_bus.subscribe(EventType.AI_RESPONSE_COMPLETED, self._on_ai_completed)
        self.event_bus.subscribe(EventType.AI_ERROR_OCCURRED, self._on_ai_error)
        self.event_bus.subscribe(EventType.AI_TOOL_CALL_STARTED, self._on_tool_call_started)
        self.event_bus.subscribe(EventType.AI_TOOL_CALL_COMPLETED, self._on_tool_call_completed)
        self.event_bus.subscribe(EventType.USER_CHIBI_CLICKED, self._on_chibi_clicked)
        self.event_bus.subscribe(EventType.USER_CHIBI_DRAGGED, self._on_chibi_dragged)
        self.event_bus.subscribe(EventType.USER_VOICE_STARTED, self._on_voice_started)
        self.event_bus.subscribe(EventType.USER_VOICE_STOPPED, self._on_voice_stopped)
    
    def _on_user_text(self, event: Event) -> None:
        """Обработка текста от пользователя"""
        text = event.data
        if not text:
            return
        
        self._ai_streaming = False
        self._first_token = True
        self.event_bus.emit(Event(EventType.CHIBI_STATE_CHANGED, ChibiState.THINKING.name))
        self.event_bus.emit(Event(EventType.CHIBI_ANIMATION_CHANGED, AnimationType.THINK.value))
        self.event_bus.emit(Event(EventType.CHAT_PROCESSING_CHANGED, True))
        self.api_service.send_message(text)
        log.info(f"Sending message to AI: {text}")

    def _on_ai_token(self, event: Event) -> None:
        """Получен токен от AI"""
        token = event.data
        if self._first_token:
            self._first_token = False
            self._ai_streaming = True
            
            self.event_bus.emit(Event(EventType.CHIBI_STATE_CHANGED, ChibiState.TALKING.name))
            self.event_bus.emit(Event(EventType.CHIBI_ANIMATION_CHANGED, AnimationType.TALK.value))
            self.bubble_vm.show("")
        
        self.bubble_vm.append_token(token)

    def _on_ai_completed(self, event: Event) -> None:
        """AI завершил генерацию"""
        self._ai_streaming = False
        self._first_token = False
        
        self.event_bus.emit(Event(EventType.CHIBI_STATE_CHANGED, ChibiState.IDLE.name))
        self.event_bus.emit(Event(EventType.CHIBI_ANIMATION_CHANGED, AnimationType.IDLE.value))
        self.event_bus.emit(Event(EventType.CHAT_PROCESSING_CHANGED, False))

    def _on_ai_error(self, event: Event) -> None:
        """Ошибка AI"""
        self._ai_streaming = False
        self._first_token = False
        error_msg = event.data or "Unknown error"
        self.bubble_vm.show(f"{error_msg}")
        
        self.event_bus.emit(Event(EventType.CHIBI_STATE_CHANGED, ChibiState.IDLE.name))
        self.event_bus.emit(Event(EventType.CHIBI_ANIMATION_CHANGED, AnimationType.IDLE.value))
        self.event_bus.emit(Event(EventType.CHAT_PROCESSING_CHANGED, False))
    
    def _on_tool_call_started(self, event: Event) -> None:
        """Начало вызова инструмента"""
        self.event_bus.emit(Event(EventType.CHIBI_STATE_CHANGED, ChibiState.PROCESSING.name))
        self.event_bus.emit(Event(EventType.CHIBI_ANIMATION_CHANGED, AnimationType.PROCESS.value))
    
    def _on_tool_call_completed(self, event: Event) -> None:
        """Завершение вызова инструмента"""
        self.event_bus.emit(Event(EventType.CHIBI_STATE_CHANGED, ChibiState.TALKING.name))
        self.event_bus.emit(Event(EventType.CHIBI_ANIMATION_CHANGED, AnimationType.TALK.value))
    
    def _on_chibi_clicked(self, event: Event) -> None:
        """Клик по чиби"""
        self.bubble_vm.show()
        self.chat_vm.show()
    
    def _on_chibi_dragged(self, event: Event) -> None:
        """Перетаскивание чиби"""
        x, y = event.data
        self.position_service.on_chibi_moved(x, y)
    
    def _on_voice_started(self, event: Event) -> None:
        """Начало голосового ввода"""
        self.event_bus.emit(Event(EventType.CHIBI_STATE_CHANGED, ChibiState.LISTENING.name))
        self.event_bus.emit(Event(EventType.CHIBI_ANIMATION_CHANGED, AnimationType.IDLE.value))
        self.api_service.start_recording()

    def _on_voice_stopped(self, event: Event) -> None:
        """Остановка голосового ввода"""
        self.api_service.stop_recording()
    def initialize(self) -> None:
        """Инициализация всех компонентов"""
        self.animation_service.initialize()
        self.api_service.initialize()
    
    def cleanup(self) -> None:
        """Очистка ресурсов"""
        self.animation_service.cleanup()
        self.api_service.cleanup()