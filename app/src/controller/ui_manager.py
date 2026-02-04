from PySide6.QtCore import QObject
from app.src.ui import *


class UIManager(QObject):
    def __init__(self, components: dict):
        super().__init__()
        self.chat: Chat = components.get("chat")
        self.message: Message = components.get("message")
        self.lina: Lina = components.get("lina")
        self.voice_button: VoiceButton = components.get("voice_button")