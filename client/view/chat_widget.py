from PySide6.QtWidgets import QLineEdit, QPushButton, QHBoxLayout, QWidget
from PySide6.QtGui import QIcon, Qt
from .base_widget import BaseWidget
from viewmodel.chat_viewmodel import ChatViewModel


class ChatWidget(BaseWidget):
    """Виджет мини-чата"""
    
    def __init__(self, viewmodel: ChatViewModel):
        super().__init__()
        self._vm = viewmodel
        
        self._input = QLineEdit()
        self._input.setPlaceholderText("Write a message...")
        self._input.setMinimumWidth(250)
        self.setStyleSheet(
        """QLineEdit {
                background: rgba(82, 156, 247, 80);
                border: 1px solid gray;
                border-radius: 5px;
                padding: 10px;
                font-family: 'Comic Sans MS', cursive;
                font-size: 20px;
                color: white;          
        }""")
        
        # Voice button styles
        self._voice_btn = QPushButton()
        self._voice_btn.setFixedSize(40, 40)
        self._voice_btn.setStyleSheet("""
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
        self._voice_btn.setIcon(QIcon("client/assets/svg/voice.svg"))
        self._voice_btn.setIconSize(self._voice_btn.size() * 0.9)
        self._voice_btn.setCursor(Qt.CursorShape.PointingHandCursor)


        #Send button styles
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
        """
        )
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
        
        # Подписка на ViewModel
        self._vm.visibility_changed.connect(self._on_visibility_changed)
        self._vm.processing_changed.connect(self._on_processing_changed)
        
        # Сигналы
        self._input.returnPressed.connect(self._submit)
        self._voice_btn.clicked.connect(self._vm.start_voice)
        self._send_btn.clicked.connect(self._submit)
        
        # Установка начального состояния
        self.setVisible(self._vm.is_visible) #type: ignore
        self._on_processing_changed(self._vm.is_processing) #type: ignore 
    
    def _submit(self):
        """Отправка сообщения"""
        text = self._input.text().strip()
        if text:
            self._input.clear()
            self._vm.send_message(text)
    
    def _on_visibility_changed(self, visible: bool):
        """Обработка изменения видимости из ViewModel"""
        self.setVisible(visible)
    
    def _on_processing_changed(self, is_processing: bool):
        """Изменение статуса обработки"""
        if is_processing:
            self._input.setEnabled(False)
            self._input.setPlaceholderText("Thinking...")
        else:
            self._input.setEnabled(True)
            self._input.setPlaceholderText("Write a message...")