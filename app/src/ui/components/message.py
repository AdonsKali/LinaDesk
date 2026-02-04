from .animation import Animation
from PySide6.QtGui import QPaintEvent
from PySide6.QtWidgets import QWidget, QTextEdit
from PySide6.QtCore import Qt, QTimer, QPoint, QRect, Signal
from PySide6.QtGui import QPainter, QPolygon, QBrush, QFont, QTextOption

class Message(QWidget, Animation):

    show_text = Signal(dict)
    hide_bubble = Signal(int)
    realtime_text = Signal(str)


    def __init__(self):
        QWidget.__init__(self, obj=self)
        self._m_char_timer: QTimer = QTimer()
        self.m_pos: str = ""
        self._m_full_text: str = ""
        self._m_visible_text: str = ""
        self._m_current_char: int = 0
        self._m_character_pos: QPoint
        self._anim_progress: float = 0.0
        self._animating: bool = True
        self._anim_reverse: bool = False 
        self._hold_timer = QTimer()

        #Connects
        self._m_char_timer.timeout.connect(self.__print_next_char)
        self.show_text.connect(self.__set_text)
        self.hide_bubble.connect(self.__hide_bub)
        self.realtime_text.connect(self.__append_realtime_text)

        self._text_edit = QTextEdit(self)
        self._text_edit.setReadOnly(True)
        self._text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._text_edit.setFrameShape(QTextEdit.NoFrame)
        self._text_edit.setFont(QFont("Arial", 16))
        self._text_edit.setWordWrapMode(QTextOption.WrapMode.WordWrap)
        
        self._text_edit.setStyleSheet("""
            QTextEdit {
                background: transparent;
                color: black;
                border: none;
            }

            QScrollBar:vertical {
                background: transparent;
                width: 8px;
                margin: 4px 0 4px 0;
            }

            QScrollBar::handle:vertical {
                background: rgba(100, 100, 100, 180);
                border-radius: 4px;
                min-height: 20px;
            }

            QScrollBar::handle:vertical:hover {
                background: rgba(60, 60, 60, 200);
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0;
                border: none;
                background: none;
            }

            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        self.setFixedSize(300,150)


    def resizeEvent(self, event):
        self._text_rect = QRect(20, 20, self.width() - 40, self.height() - 50)
        self._text_edit.setGeometry(self._text_rect)


    def __append_realtime_text(self, chunk: str):
        if not self._animating or self._anim_progress == 0.0:
            self._animate_from_tail()
        current = self._text_edit.toPlainText()
        current += chunk
        self._text_edit.setPlainText(current)
        sb = self._text_edit.verticalScrollBar()
        sb.setValue(sb.maximum())


    def set_character_pos(self, pos: QPoint):
        self._m_character_pos = pos;
        self.update()


    def __set_text(self, args: dict):
        if self._hold_timer.isActive():
            self._hold_timer.stop()
        self._animate_from_tail()
        self._m_full_text = args.get('wake_word')
        self._m_current_char = 0
        self._text_edit.clear()
        self._m_char_timer.start(args.get('rate'))


    def __hide_bub(self, time: int):
        """Скрыть через определенное время"""
        if self._hold_timer.isActive():
            self._hold_timer.stop()
        self._hold_timer.singleShot(time, self._animate_to_tail)


    def __print_next_char(self):
        if self._m_current_char < len(self._m_full_text):
            current = self._text_edit.toPlainText()
            current += self._m_full_text[self._m_current_char]
            self._text_edit.setPlainText(current)
            self._m_current_char += 1
            sb = self._text_edit.verticalScrollBar()
            sb.setValue(sb.maximum())
        else:
            self._m_char_timer.stop()
            self._hold_timer.singleShot(6000, self._animate_to_tail)

    def __create_bubble_tail(self, is_right: bool, is_top:bool):
        x_base = self.bubble_rect.right() if is_right else self.bubble_rect.left()
        y_base = self.bubble_rect.top() if is_top else self.bubble_rect.bottom()
        
        x_sign = -1 if is_right else 1
        y_sign = -1 if is_top  else 1

        if self._animating and (self._anim_progress == 1.0 or self._anim_progress == 0.0):
            return QPolygon([
            QPoint(x_base + x_sign*20*self._anim_progress, y_base),
            QPoint(x_base + x_sign*10*self._anim_progress, y_base),
            QPoint(x_base - x_sign*10*self._anim_progress, y_base + y_sign*20)
        ])
        
        return QPolygon([
            QPoint(x_base + x_sign*20, y_base),
            QPoint(x_base + x_sign*10, y_base),
            QPoint(x_base - x_sign*10, y_base + y_sign*20)
        ])


    def paintEvent(self, event: QPaintEvent):
        self.painter: QPainter = QPainter(self)
        self.painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.painter.setPen(Qt.PenStyle.NoPen)
        self.painter.setBrush(QBrush(Qt.GlobalColor.white))

        full_rect: QRect = QRect(10, 10, self.width() - 20, self.height() - 30)

        if self._animating:
            tail_point: QPoint = QPoint(full_rect.left(), full_rect.bottom())  # можно адаптировать под m_pos
            w = full_rect.width() * self._anim_progress
            h = full_rect.height() * self._anim_progress
            x = tail_point.x()
            y = tail_point.y() - h
            self.bubble_rect = QRect(int(x), int(y), int(w), int(h))
        else:
            self.bubble_rect = full_rect

        self.painter.drawRoundedRect(self.bubble_rect, 12, 12)
        match self.m_pos:
            case "left-top":
                self.tail = self.__create_bubble_tail(False, True)
            case "bottom-left":
                self.tail = self.__create_bubble_tail(False, False)
            case "right-bottom":
                self.tail = self.__create_bubble_tail(True, False)
            case "right-top":
                self.tail = self.__create_bubble_tail(True, True)
            case _:
                self.tail = self.__create_bubble_tail(False, False)
    
        self.painter.drawPolygon(self.tail);
        self.painter.end()
        

    def _animate_from_tail(self):
        if self._anim_progress != 1.0:
            self._anim_progress = 0.0
            self._anim_reverse = False
            self.show()
            self.start_animation(18)


    def _animate_to_tail(self):
        if self._anim_progress != 0.0:
            self._text_edit.clear()
            self._anim_progress = 1.0
            self._anim_reverse = True
            self.start_animation(18)


    def _update_animation(self):
        if not self._anim_reverse:
            if self._anim_progress < 1.0:
                self._anim_progress += 0.05
            else:
                self._anim_progress = 1.0
                self.animation_delay.stop()
        else:
            if self._anim_progress > 0.0:
                self._anim_progress -= 0.05
            else:
                self._anim_progress = 0.0
                self.animation_delay.stop()
                self.hide()
        self.update()
        