from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtGui import QMouseEvent
from client.viewmodels.chibi_viewmodel import ChibiViewModel
from client.services.animation_service import AnimationService

class ChibiView(QLabel):
    """Виджет чиби персонажа"""
    
    position_changed = Signal(int, int)
    clicked = Signal()
    double_clicked = Signal()
    
    def __init__(self, viewmodel: ChibiViewModel, animation_service: AnimationService):
        super().__init__()
        self._vm = viewmodel
        self._animation_service = animation_service
        self._drag_start = None
        
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setScaledContents(True)
        self.resize(200, 200)

        self._vm.animation_changed.connect(self._on_animation_changed)
        self._vm.position_changed.connect(self.move)
        self._on_animation_changed("idle")
    
    def _on_animation_changed(self, animation_name: str) -> None:
        """Смена анимации"""
        from models.chibi_model import AnimationType
        animation = AnimationType(animation_name)
        movie = self._animation_service.play_animation(animation)
        if movie:
            self.setMovie(movie)
    
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Нажатие мыши"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.globalPosition().toPoint() - self.pos()
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Перемещение мыши"""
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_start:
            new_pos = event.globalPosition().toPoint() - self._drag_start
            self.move(new_pos)
            self._vm.on_dragged(new_pos.x(), new_pos.y())
            self.position_changed.emit(new_pos.x(), new_pos.y())
    
    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Отпускание мыши"""
        self._drag_start = None
        super().mouseReleaseEvent(event)
    
    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """Двойной клик"""
        self._vm.on_clicked()
        self.double_clicked.emit()