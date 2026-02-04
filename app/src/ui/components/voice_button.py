from PySide6.QtWidgets import QPushButton
from PySide6.QtGui import QIcon, QCursor
from PySide6.QtCore import QSize, QEvent, Qt, Signal
from paths import MEDIA


class VoiceButton(QPushButton):

    pressed_signal = Signal()

    def __init__(self):
        super().__init__()
        self.setStyleSheet("""
            QPushButton{
                border-radius: full;
            }
        """)

        self.setIcon(QIcon(f"{MEDIA}/voice_components/voice.svg"))
        self.installEventFilter(self)
        self.setIconSize(QSize(40,40))
        self.pressed.connect(lambda: self.pressed_signal.emit())


    def eventFilter(self, obj, event: QEvent):
        if event.type() == QEvent.Enter:
            self.setCursor(QCursor(Qt.PointingHandCursor))
            self.setIcon(QIcon(f"{MEDIA}/voice_components/voice-hover.svg"))
        elif event.type() == QEvent.Leave or event.type() == QEvent.MouseButtonRelease:
            self.setCursor(QCursor(Qt.ArrowCursor))
            self.setIcon(QIcon(f"{MEDIA}/voice_components/voice.svg"))
        elif event.type() == QEvent.MouseButtonPress or event.type() == QEvent.Enter:
            self.setCursor(QCursor(Qt.PointingHandCursor))
            self.setIcon(QIcon(f"{MEDIA}/voice_components/voice-active.svg"))
        return super().eventFilter(obj, event)