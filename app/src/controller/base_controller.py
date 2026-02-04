from .logger import log
from random import randint
from settings import CONFIG, _
from app.src.ui.init_components import *
from .state import LinaStateMachine, LinaState
from PySide6.QtCore import QObject, Slot, QTimer
from app.src.controller.api_client import APIClient  


class BaseController(QObject):

    def __init__(self, debug: bool = False):
        super().__init__()
        self.debug = debug
        self.state_machine = LinaStateMachine()
        
        self.api_client = APIClient()  
        self.api_client.connect_agent()
        self.api_client.connect_recognition()

        self.chat: Chat = chat
        self.message: Message = message
        self.lina: Lina = lina
        self.voice_button: VoiceButton = voice_button

        # MESSAGE
        self.wake_words: list = _('trigger_words')
        self._setup_signals()


    # ---------------- SIGNALS ----------------
    def _setup_signals(self):
        # CHAT
        if self.chat:
            self.chat.prompt_submitted.connect(self.on_chat_request)
            self.wake_timer = QTimer()
            self.wake_timer.timeout.connect(self.__update_sleep)

        # Lina
        if self.lina:
            self.lina.wake_up_signal.connect(self.wake_up_lina)

        # Voice button
        if self.voice_button:
            self.voice_button.pressed_signal.connect(self.on_voice_button_pressed)


    # ---------------- SLOTS ----------------
    @Slot(str)
    def on_realtime_text(self, token: str):
        """Отправляем токены из AI в message в realtime"""
        self.message.realtime_text.emit(token)


    @Slot(list)
    def on_chat_request(self, data: list):
        """Пришёл запрос из чата → меняем state и вызываем AI через API"""
        try:
            
            if hasattr(self.message, '_hold_timer'):
                self.message._hold_timer.stop()
            
            self.state_machine.set_state(LinaState.THINKING)
            self._send_to_ai(data[1])
            
        except Exception as e:
            log("error", "AI", f"Request error: {e}")
            if self.chat:
                self.chat.update_signal.emit()
            self.state_machine.set_state(LinaState.IDLE)

    @Slot()
    def on_ai_done(self):
        """AI завершил работу """
        try:
            log("info", "AI", "done.")
            if hasattr(self.message, '_hold_timer'):
                self.message._hold_timer.singleShot(4000, self.message._animate_to_tail)
            
            if self.chat:
                self.chat.update_signal.emit()
            
            self.state_machine.set_state(LinaState.IDLE)
        except Exception as e:
            log("error", "AI", f"{e}")
            self.state_machine.set_state(LinaState.IDLE)

    @Slot()
    def on_voice_button_pressed(self):
        """Обработка нажатия кнопки голоса"""
        try:
            log("info", "VOICE", "Voice button pressed")
            self.state_machine.set_state(LinaState.LISTENING) 
            self.api_client.set_recognition_callbacks(
                on_result=lambda text: self._send_to_ai(text),
                on_error=lambda e: log("error", "RECOGNIZE", f"{e}"),
            )
            self.api_client.start_recognition()

        except Exception as e:
            log("error", "VOICE", f"{e}")
            self.state_machine.set_state(LinaState.IDLE)

    @Slot()
    def on_recognize_complete(self, text):
        log("info", "RECOGNIZE", f"{text}")
        self.state_machine.set_state(LinaState.IDLE) 

    @Slot()
    def wake_up_lina(self):
        """Принимает double click от чиби"""
        try:
            if self.state_machine.state == LinaState.IDLE:
                self.wake_timer.start(8000)
                
                if self.chat:
                    self.chat.show()
                
                if self.voice_button:
                    self.voice_button.show()
                wake_word = self.wake_words[randint(0, len(self.wake_words)-1)]
                if self.message:
                    self.message.show_text.emit([wake_word, 50])
                
                self.state_machine.set_state(LinaState.TALKING)
                log("info", "LINA", "wake upped")
            else:
                log("warning", "LINA", "Not wake upped, Lina is not in IDLE state !")
        except Exception as e:
            log("error", "LINA", f"{e}")

    def __update_sleep(self):
        if self.chat and not self.chat.hasFocus():
            self.chat.hide()
            
            if self.voice_button:
                self.voice_button.hide()
            
            self.wake_timer.stop()
        
        self.state_machine.set_state(LinaState.IDLE)

    # ---------------- PRIVATE METHODS ----------------
    def _send_to_ai(self, prompt: str):
        """Отправляет промпт на сервер AI"""
        try:
            log("info", "API", f"Sending to AI: {prompt[:50]}...")
            
            # Отправляем запрос на генерацию
            self.api_client.set_agent_callbacks(
                on_token=self.on_realtime_text,
                on_complete=self.on_ai_done,
                on_error=lambda e: self._handle_ai_error(e),
            )
            self.api_client.generate_text(prompt)
            
        except Exception as e:
            log("error", "API", f"Send error: {e}")
            self.state_machine.set_state(LinaState.IDLE)

    def _handle_ai_error(self, error: str):
        """Обработка ошибок AI"""
        log("error", "AI", f"Generation error: {error}")
        if self.chat:
            self.chat.update_signal.emit()
        self.state_machine.set_state(LinaState.IDLE)

