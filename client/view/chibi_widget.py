import logging
from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtGui import QMouseEvent
from .base_widget import BaseWidget

logger = logging.getLogger(__name__)


class ChibiWidget(BaseWidget):
    """Виджет чиби"""
    
    position_changed = Signal(QPoint)
    
    def __init__(self, viewmodel, animation_service):
        super().__init__()
        self._vm = viewmodel
        self._animation_service = animation_service
        
        logger.info("Creating ChibiWidget...")
        
        # Создаем метку для отображения
        self._label = QLabel(self)
        self._label.setScaledContents(True)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Устанавливаем размер
        self.resize(200, 200)
        
        # Устанавливаем тестовый цветной фон для проверки
        self.setStyleSheet("""
            ChibiWidget {
                background-color: rgba(100, 150, 200, 200);
                border: 3px solid red;
                border-radius: 10px;
            }
        """)
        
        # Устанавливаем тестовое изображение
        
        # Подписка на анимации
        self._vm.animation_changed.connect(self._on_animation_changed)
        
        # Подписка на позицию
        self._vm.position_changed.connect(self._on_position_changed)
        
        logger.info("ChibiWidget created successfully")
    
    def _on_animation_changed(self, animation_name: str):
        """Смена анимации"""
        movie = self._animation_service.get_animation(animation_name)
        if movie:
            self._label.setMovie(movie)
            movie.start()
        else:
            logger.warning(f"Animation not found: {animation_name}")
    
    def _on_position_changed(self, x: int, y: int):
        """Изменение позиции"""
        self.move(x, y)
        self.position_changed.emit(QPoint(x, y))
    
    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """Двойной клик"""
        self._vm.wake_up()
        event.accept()
    
    def mousePressEvent(self, event: QMouseEvent):
        """Нажатие мыши"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = event.globalPosition().toPoint() - self.pos()
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Перетаскивание - ИСПРАВЛЕНО"""
        if event.buttons() == Qt.MouseButton.LeftButton and hasattr(self, '_drag_position') and self._drag_position:
            new_pos = event.globalPosition().toPoint() - self._drag_position
            self.move(new_pos)
            # Правильно передаем координаты как отдельные числа, а не как Event
            self._vm.on_dragged(new_pos.x(), new_pos.y())
            self.position_changed.emit(new_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Отпускание мыши"""
        self._drag_position = None
        super().mouseReleaseEvent(event)
    
    def showEvent(self, event):
        """Виджет показан"""
        super().showEvent(event)
    
    def resizeEvent(self, event):
        """Изменение размера"""
        self._label.resize(self.size())
        logger.debug(f"Resized to: {self.size()}")