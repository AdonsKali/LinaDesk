import random

from PySide6.QtCore import QObject, QTimer
from core import Event, EventType,EventBus
from model.models import ChibiModel, ChibiState, Position, MessageModel, ChatModel


class EventHandler(QObject):
    """
    Централизованный обработчик событий
    """
    
    def __init__(self, event_bus: EventBus):
        super().__init__()
        self._event_bus = event_bus
        
        # Состояние приложения
        self.chibi = ChibiModel()
        self.message = MessageModel()
        self.chat = ChatModel()
        
        # Флаг для защиты от рекурсии при обновлении
        self._updating = False
        
        # Таймеры
        self._hide_message_timer = QTimer()
        self._hide_message_timer.setSingleShot(True)
        self._hide_message_timer.timeout.connect(self._on_hide_message_timeout)
        
        self._hide_chat_timer = QTimer()
        self._hide_chat_timer.setSingleShot(True)
        self._hide_chat_timer.timeout.connect(self._on_hide_chat_timeout)
        
        # Сервисы
        self.animation_service = None
        self.api_client = None
        
        # Регистрируем обработчики
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Регистрация всех обработчиков событий"""
        self._handlers = {
            EventType.USER_TEXT_SUBMITTED: self._handle_text_submitted,
            EventType.USER_VOICE_PRESSED: self._handle_voice_pressed,
            EventType.USER_CHIBI_CLICKED: self._handle_chibi_clicked,
            EventType.USER_CHIBI_DRAGGED: self._handle_chibi_dragged,
            EventType.TOOL_CALL_START: self._handle_tool_call,
            EventType.TOOL_CALL_END: self._handle_tool_call_end,
            EventType.AI_STREAM_START: self._handle_ai_start,
            EventType.AI_TOKEN: self._handle_ai_token,
            EventType.AI_STREAM_END: self._handle_ai_end,
            EventType.AI_ERROR: self._handle_ai_error,
            EventType.UI_SHOW_CHAT: self._handle_show_chat,
            EventType.UI_HIDE_CHAT: self._handle_hide_chat,
            EventType.UI_SHOW_MESSAGE: self._handle_show_message,
            EventType.UI_HIDE_MESSAGE: self._handle_hide_message,
            EventType.UI_UPDATE_POSITIONS: self._handle_update_positions,
        }
        
        # Подписываемся на все события
        for event_type in self._handlers:
            self._event_bus.subscribe(event_type, self._on_event)
    
    def _on_event(self, event: Event):
        """Общий обработчик событий"""
        if event.type in self._handlers:
            handler = self._handlers[event.type]
            try:
                handler(event)
            except Exception as e:
                import traceback
                traceback.print_exc()
    
    # ==================== ОБРАБОТЧИКИ СОБЫТИЙ ====================
    def _handle_text_submitted(self, event: Event):
        """Пользователь отправил текст"""
        text = event.data
        
        # Обновляем состояние
        self.chat.is_processing = True
        self.chat.input_text = text
        
        self.chibi.state = ChibiState.THINKING
        self.chibi.current_animation = "think"
        
        # Отправляем обновления
        self._emit_updates()
        
        # Отправляем в API
        if self.api_client:
            self.api_client.send_message(text)
        
        # Сбрасываем таймер
        self._reset_hide_chat_timer()
    
    def _handle_voice_pressed(self, event: Event):
        """Нажата голосовая кнопка"""
        
        self.chibi.state = ChibiState.LISTENING
        self.chibi.current_animation = "idle"
        
        self._emit_updates()
        
        if self.api_client:
            self.api_client.start_voice_recognition()
        
        self._reset_hide_chat_timer()
    
    def _handle_chibi_clicked(self, event: Event):
        """Клик по чиби"""
        # Пробуждение
        if self.chibi.state == ChibiState.SLEEPING or self.chibi.state == ChibiState.IDLE:
            self.chibi.state = ChibiState.IDLE
            self.chibi.current_animation = "idle"
        
            # Показываем UI
            self.chat.is_visible = True
            self.message.is_visible = True
            self.message.text = "How can I help you?"
            
            self._emit_updates()
            
            # Планируем скрытие сообщения
            self._hide_message_timer.start(5000)
            self._reset_hide_chat_timer()
    
    def _handle_chibi_dragged(self, event: Event):
        """Перетаскивание чиби"""
        if isinstance(event.data, (tuple, list)) and len(event.data) == 2:
            x, y = event.data
            
            self.chibi.position = Position(x, y)
            self._emit_updates()

            self._event_bus.emit(Event(EventType.UI_UPDATE_POSITIONS, (x, y)))
            
            self._reset_hide_chat_timer()


    def _handle_tool_call(self, event: Event):
        """Вызван вызов инструмента"""
        if self.chibi.state == ChibiState.THINKING:
            self.chibi.state = ChibiState.PROCESSING
            self.chibi.current_animation = "process"

            self._emit_updates()

    def _handle_tool_call_end(self, event: Event):
        """Инструмент завершен"""
        if self.chibi.state == ChibiState.PROCESSING:
            self.chibi.state = ChibiState.TALKING
            self.chibi.current_animation = "talk"
            self._emit_updates()

    def _handle_ai_start(self, event: Event):
        """AI начал генерацию"""
        
        self.chibi.state = ChibiState.TALKING
        self.chibi.current_animation = "talk"
        
        self._emit_updates()
    
    def _handle_ai_token(self, event: Event):
        """Получен токен от AI"""
        token = event.data
        
        self.message.text += token
        
        if self.chibi.state == ChibiState.THINKING or self.chibi.state == ChibiState.PROCESSING:
            self.chibi.state = ChibiState.TALKING
            self.chibi.current_animation = "talk"
        if not self.message.is_visible:
            self.message.is_visible = True
        
        self._emit_updates()
    
    def _handle_ai_end(self, event: Event):
        """AI завершил генерацию"""
        
        self.chibi.state = ChibiState.IDLE
        self.chibi.current_animation = "idle"
        self.chat.is_processing = False
        
        self._emit_updates()
        
        # Планируем скрытие сообщения через 6 секунд
        self._hide_message_timer.start(6000)
    
    def _handle_ai_error(self, event: Event):
        """Ошибка AI"""
        error = event.data

        
        self.chibi.state = ChibiState.IDLE
        self.chat.is_processing = False
        self.message.text = f"Error: {error}"
        self.message.is_visible = True
        
        self._emit_updates()
        
        self._hide_message_timer.start(5000)
    
    def _handle_show_chat(self, event: Event):
        """Показать чат"""
        if not self.chat.is_visible:
            self.chat.is_visible = True
            self._emit_updates()
        self._reset_hide_chat_timer()
    
    def _handle_hide_chat(self, event: Event):
        """Скрыть чат"""
        if self.chat.is_visible:
            self.chat.is_visible = False
            self._emit_updates()
    
    def _handle_show_message(self, event: Event):
        """Показать сообщение"""
        if not self.message.is_visible:
            self.message.is_visible = True
            if event.data:
                self.message.text = event.data
            self._emit_updates()
    
    def _handle_hide_message(self, event: Event):
        """Скрыть сообщение"""
        if self.message.is_visible:
            self.message.is_visible = False
            self.message.text = ""
            self._emit_updates()
    
    def _handle_update_positions(self, event: Event):
        """Обработка обновления позиций UI элементов"""
        # Это событие просто передается дальше, если нужно обновить позиции
        pass

    # ==================== ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ ====================
    
    def _emit_updates(self):
        """
        Отправляем обновления во ViewModels
        Используем QTimer.singleShot для избежания рекурсии
        """
        if self._updating:
            return
        
        self._updating = True
        
        try:
            # Отправляем события для чиби
            self._event_bus.emit(Event(EventType.CHIBI_STATE_CHANGED, self.chibi.state.name))
            self._event_bus.emit(Event(EventType.CHIBI_ANIMATION_CHANGED, self.chibi.current_animation))
            self._event_bus.emit(Event(EventType.CHIBI_POSITION_CHANGED, 
                                       (self.chibi.position.x, self.chibi.position.y)))
            
            # Отправляем события для чата
            if self.chat.is_visible:
                self._event_bus.emit(Event(EventType.UI_SHOW_CHAT))
            else:
                self._event_bus.emit(Event(EventType.UI_HIDE_CHAT))
            
            # Отправляем события для сообщения
            if self.message.is_visible:
                self._event_bus.emit(Event(EventType.UI_SHOW_MESSAGE, self.message.text))
            else:
                self._event_bus.emit(Event(EventType.UI_HIDE_MESSAGE))
            
            # Отправляем статус обработки
            self._event_bus.emit(Event(EventType.CHAT_PROCESSING_CHANGED, self.chat.is_processing))
            
        finally:
            self._updating = False
    
    def _on_hide_message_timeout(self):
        """Таймаут скрытия сообщения"""
        if self.message.is_visible:
            self.message.is_visible = False
            self.message.text = ""
            self._emit_updates()
    
    def _on_hide_chat_timeout(self):
        """Таймаут скрытия чата"""
        if not self.chat.is_processing and self.chat.is_visible:
            self.chat.is_visible = False
            self._emit_updates()
    
    def _reset_hide_chat_timer(self):
        """Сброс таймера скрытия чата"""
        self._hide_chat_timer.start(10000)
    
    def set_services(self, animation_service, api_client):
        """Установка сервисов"""
        self.animation_service = animation_service
        self.api_client = api_client
        
        if self.api_client:
            self.api_client.tool_call_received.connect(lambda: self._event_bus.emit(Event(EventType.TOOL_CALL_START)))
            self.api_client.generation_complete.connect(lambda: self._event_bus.emit(Event(EventType.TOOL_CALL_END)))
            self.api_client.token_received.connect(lambda token: self._event_bus.emit(Event(EventType.AI_TOKEN, token)))
            self.api_client.generation_complete.connect(lambda: self._event_bus.emit(Event(EventType.AI_STREAM_END)))
            self.api_client.generation_error.connect(lambda error: self._event_bus.emit(Event(EventType.AI_ERROR, error)))
            self.api_client.recognition_result.connect(lambda text: self._event_bus.emit(Event(EventType.USER_TEXT_SUBMITTED, text)))
            self.api_client.recognition_error.connect(lambda error: self._event_bus.emit(Event(EventType.AI_ERROR, error)))