from PySide6.QtWidgets import QWidget
from PySide6.QtCore import QSize, Qt

class BaseWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.SplashScreen | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        # self.set_object(self)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_offset = event.pos()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            new_pos = self.pos() + (event.pos() - self.drag_offset)
            self.move(new_pos)


    def sizeHint(self) -> QSize:
        right = []
        bottom = []
        for child in self.findChildren(QWidget, options=Qt.FindDirectChildrenOnly):
            if child.x() < 0:
                child.move(0, child.y())
            if child.y() < 0:
                child.move(child.x(), 0)
            size = child.sizeHint() if child.sizeHint().isValid() else child.size()
            right.append(child.x() + size.width())
            bottom.append(child.y() + size.height())
        width = max(right) if right else 0
        height = max(bottom) if bottom else 0
        return QSize(width, height)


    

        

        