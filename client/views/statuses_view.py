from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from client.viewmodels.statuses_viewmodel import StatusesViewModel

class StatusesView(QWidget):
    """Виджет отображения статусов чиби"""
    
    def __init__(self, viewmodel: StatusesViewModel):
        super().__init__()
        self._vm = viewmodel
        
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.setFixedSize(50, 180)
        
        self._layout = QVBoxLayout(self)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        self._layout.setSpacing(5)
        self._layout.setContentsMargins(5, 5, 5, 5)
        
        self.setStyleSheet("""
            QWidget {
                background-color: rgba(0, 0, 0, 0.6);
                border-radius: 10px;
            }
            QLabel {
                background-color: rgba(255, 255, 255, 0.2);
                border-radius: 5px;
                padding: 5px;
            }
            QLabel:hover {
                background-color: rgba(255, 255, 255, 0.4);
            }
        """)
        
        self._vm.statuses_updated.connect(self._update_display)
        self._update_display()
    
    def _update_display(self) -> None:
        """Обновление отображения статусов"""
        # Очищаем layout
        for i in reversed(range(self._layout.count())):
            widget = self._layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        # Добавляем все статусы
        for status in self._vm.get_statuses():
            label = QLabel()
            label.setFixedSize(40, 40)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setToolTip(status.text)
            label.setText(status.icon_path)  # Эмодзи
            label.setStyleSheet("font-size: 24px;")
            
            # Сохраняем ID статуса для удаления
            label.setProperty("status_id", status.id)
            label.setProperty("file_path", status.data.get("file_path") if status.data else None)
            
            # Клик правой кнопкой для удаления
            def mousePressEvent(event, status_id=status.id, file_path=None):
                if event.button() == Qt.MouseButton.RightButton:
                    self._vm.remove_file_status(file_path) if file_path else None
            
            label.mousePressEvent = mousePressEvent
            
            self._layout.addWidget(label)
        
        # Добавляем растяжку в конец
        self._layout.addStretch()
        
        # Скрываем виджет, если нет статусов
        self.setVisible(len(self._vm.get_statuses()) > 0)