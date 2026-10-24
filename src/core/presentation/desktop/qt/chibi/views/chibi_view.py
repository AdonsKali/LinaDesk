from PySide6.QtWidgets import QLabel
from PySide6.QtCore import QSize, Qt, Signal, QTimer, QRectF
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QMouseEvent, QPainter, QColor, QPen
import math
import random
from ..viewmodels.chibi_viewmodel import ChibiViewModel
from ..services.animation_service import AnimationService

class ChibiView(QLabel):
    """Виджет чиби персонажа"""
    
    position_changed = Signal(int, int)
    double_clicked = Signal()
    file_enter = Signal()
    file_leave = Signal()
    file_dropped = Signal(str)
    
    def __init__(self, viewmodel: ChibiViewModel, animation_service: AnimationService):
        super().__init__()
        self._vm = viewmodel
        self._animation_service = animation_service
        self._drag_start = None
        self._fallback = True
        self._animation_name = "idle"
        self._emotion = "neutral"
        self._phase = 0
        self._walk_target = None
        self._velocity_y = 0.0
        self.setAcceptDrops(True)
        
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
        self._motion_timer = QTimer(self)
        self._motion_timer.timeout.connect(self._advance)
        self._motion_timer.start(33)
    
    def _on_animation_changed(self, animation_name: str) -> None:
        """Смена анимации"""
        from ..models.chibi_model import AnimationType
        animation = AnimationType(animation_name)
        self._animation_name = animation_name
        movie = self._animation_service.play_animation(animation)
        self._fallback = movie is None
        if movie:
            movie.setScaledSize(QSize(200,200))
            self.setMovie(movie)
        else:
            self.setMovie(None)
            self.update()

    def set_emotion(self, emotion):
        self._emotion = emotion
        self.setToolTip(f"Lina · {emotion}")
        self.update()

    def walk(self, direction):
        if self._drag_start is not None:
            return
        bounds = self.screen().availableGeometry()
        distance = random.randint(70, 220)
        sign = -1 if direction == "left" else 1 if direction == "right" else random.choice((-1, 1))
        self._walk_target = max(bounds.left(), min(
            self.x() + sign * distance, bounds.right() - self.width() + 1))

    def _advance(self):
        self._phase += 0.12
        if self._drag_start is None and self.isVisible():
            bounds = self.screen().availableGeometry()
            floor = bounds.bottom() - self.height() + 1
            new_x = max(bounds.left(), min(self.x(), bounds.right() - self.width() + 1))
            if self.y() < floor:
                self._velocity_y = min(15.0, self._velocity_y + 0.6)
                new_y = min(floor, self.y() + int(self._velocity_y))
            else:
                new_y = floor
                self._velocity_y = 0
            if new_x != self.x() or new_y != self.y():
                self.move(new_x, new_y)
                self.position_changed.emit(new_x, new_y)
        if self._walk_target is not None and self._drag_start is None:
            delta = self._walk_target - self.x()
            if abs(delta) <= 3:
                self._walk_target = None
            else:
                self.move(self.x() + (3 if delta > 0 else -3), self.y())
                self.position_changed.emit(self.x(), self.y())
        if self._fallback:
            self.update()

    def paintEvent(self, event):
        if not self._fallback:
            super().paintEvent(event)
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        bob = math.sin(self._phase) * (4 if self._walk_target is not None else 2)
        painter.translate(0, bob)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#45375d"))
        painter.drawEllipse(QRectF(49, 21, 102, 113))
        painter.setBrush(QColor("#a78bfa"))
        painter.drawRoundedRect(QRectF(66, 116, 68, 60), 24, 24)
        painter.setBrush(QColor("#ffe4d6"))
        painter.drawEllipse(QRectF(59, 40, 82, 80))
        painter.setBrush(QColor("#57406f"))
        painter.drawRoundedRect(QRectF(55, 25, 90, 32), 16, 16)
        frightened = self._emotion in ("fear", "anxiety")
        painter.setBrush(QColor("#30263f"))
        blink = int(self._phase * 5) % 100 > 96
        height = 3 if blink else 20 if frightened else 14
        for x in (79, 113):
            painter.drawEllipse(QRectF(x, 70, 9, height))
        painter.setPen(QPen(QColor("#9c5971"), 3))
        if frightened or self._animation_name == "talk":
            painter.drawEllipse(QRectF(95, 96, 10, 9 + 3 * math.sin(self._phase * 3)))
        else:
            painter.drawArc(QRectF(88, 88, 24, 15), 190 * 16, 160 * 16)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#57406f"))
        painter.drawEllipse(QRectF(67, 168, 28, 13))
        painter.drawEllipse(QRectF(106, 168, 28, 13))
        if self._animation_name in ("think", "process"):
            painter.setBrush(QColor("#ddd0ff"))
            for n in range(3):
                painter.drawEllipse(QRectF(151 + n * 12, 35 - n * 8, 7, 7))
    
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Нажатие мыши"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._walk_target = None
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
        self._velocity_y = 0
        super().mouseReleaseEvent(event)

    def closeEvent(self, event):
        self._motion_timer.stop()
        super().closeEvent(event)
    
    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """Двойной клик"""
        self._vm.on_clicked()
        self.double_clicked.emit()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._vm.on_file_enter()
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:
        self._vm.on_file_leave()

    def dropEvent(self, event: QDropEvent) -> None:
        urls = event.mimeData().urls()
        for url in urls[:3]:   # лимит 3 файла
            file_path = url.toLocalFile()
            if file_path:
                self._vm.on_file_dropped(file_path)
        event.acceptProposedAction()
