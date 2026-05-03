from PySide6.QtWidgets import QLineEdit, QPushButton, QHBoxLayout, QWidget
from PySide6.QtGui import QIcon, Qt
from client.viewmodels.chat_viewmodel import ChatViewModel

class ChatView(QWidget):
    """Виджет мини-чата"""
    
    def __init__(self, viewmodel: ChatViewModel):
        super().__init__()
        self._vm = viewmodel

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._input = QLineEdit()
        self._input.setPlaceholderText("Write a message...")
        self._input.setMinimumWidth(250)

        self._voice_btn = QPushButton()
        self._voice_btn.setFixedSize(40, 40)
        self._voice_btn.setCheckable(True) 
        self._voice_btn.setIcon(QIcon("client/assets/svg/voice.svg"))
        self._voice_btn.setIconSize(self._voice_btn.size() * 0.9)
        self._voice_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        self._voice_btn_normal_style = """
            QPushButton {
                background: rgba(0, 47, 122, 150);
                border-radius: 18px;
            }
            QPushButton:hover {
                background: rgba(120, 168, 245, 150);
            }
            QPushButton:pressed {
                background: rgba(255, 255, 255, 200);
            }
        """
        
        self._voice_btn_recording_style = """
            QPushButton {
                background: rgba(255, 0, 0, 200);
                border-radius: 18px;
                border: 2px solid rgba(255, 100, 100, 255);
            }
            QPushButton:hover {
                background: rgba(255, 50, 50, 200);
            }
        """
        
        self._voice_btn.setStyleSheet(self._voice_btn_normal_style)
        
        self._send_btn = QPushButton()
        self._send_btn.setFixedSize(40, 40)
        self._send_btn.setStyleSheet("""
            QPushButton {
                background: rgba(0, 47, 122, 150);
                border-radius: 18px;
            }
            QPushButton:hover {
                background: rgba(120, 168, 245, 150);
            }
            QPushButton:pressed {
                background: rgba(255, 255, 255, 200);
            }
        """)
        self._send_btn.setIcon(QIcon("client/assets/svg/send.svg"))
        self._send_btn.setIconSize(self._send_btn.size() * 0.9)
        self._send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Layout
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)
        layout.addWidget(self._input)
        layout.addWidget(self._voice_btn)
        layout.addWidget(self._send_btn)
        
        self.setLayout(layout)
        self.setFixedHeight(60)
        
        self.setStyleSheet("""
            QLineEdit {
                background: rgba(82, 156, 247, 80);
                border: 1px solid gray;
                border-radius: 5px;
                padding: 10px;
                font-family: 'Comic Sans MS', cursive;
                font-size: 20px;
                color: white;          
            }
        """)
        
        self._vm.visibility_changed.connect(self._on_visibility_changed)
        self._vm.processing_changed.connect(self._on_processing_changed)
        self._vm.voice_state_changed.connect(self._on_voice_state_changed)

        self._input.returnPressed.connect(self._submit)
        self._voice_btn.clicked.connect(self._on_voice_clicked)
        self._send_btn.clicked.connect(self._submit)
        self._input.installEventFilter(self)
        
        self.setVisible(self._vm.is_visible) #type: ignore
        self._on_processing_changed(self._vm.is_processing) #type: ignore
    
    def eventFilter(self, obj, event):
        """Отслеживание фокуса"""
        if obj == self._input:
            if event.type() == event.Type.FocusIn:
                self._vm.set_focus(True)
            elif event.type() == event.Type.FocusOut:
                self._vm.set_focus(False)
        return super().eventFilter(obj, event)
    
    def _on_voice_clicked(self):
        """Обработка нажатия голосовой кнопки"""
        if self._vm.is_processing:
            return
        
        if self._voice_btn.isChecked():
            self._vm.start_voice()
        else:
            self._vm.stop_voice()
    
    def _on_voice_state_changed(self, is_recording: bool):
        """Изменение состояния записи"""
        if is_recording:
            self._voice_btn.setStyleSheet(self._voice_btn_recording_style)
            self._input.setPlaceholderText("Recording...")
            self._send_btn.setEnabled(False)
            self._input.setEnabled(False)
        else:
            self._voice_btn.setStyleSheet(self._voice_btn_normal_style)
            self._voice_btn.setChecked(False)
            self._input.setPlaceholderText("Write a message...")
            self._send_btn.setEnabled(True)
            self._input.setEnabled(True)
    
    def _submit(self):
        """Отправка сообщения"""
        text = self._input.text().strip()
        if text and not self._vm.is_processing:
            self._input.clear()
            self._vm.send_message(text)
    
    def _on_visibility_changed(self, visible: bool):
        """Обработка изменения видимости"""
        self.setVisible(visible)
    
    def _on_processing_changed(self, is_processing: bool):
        """Изменение статуса обработки"""
        if is_processing:
            self._input.setEnabled(False)
            self._input.setPlaceholderText("Thinking...")
            self._send_btn.setEnabled(False)
            if self._voice_btn.isChecked():
                self._vm.stop_voice()
        else:
            self._input.setEnabled(True)
            self._input.setPlaceholderText("Write a message...")
            self._send_btn.setEnabled(True)