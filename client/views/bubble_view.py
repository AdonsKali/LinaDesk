import random
from PySide6.QtWidgets import QWidget, QTextEdit
from PySide6.QtCore import Qt, QPoint, QRect, QTimer, Signal
from PySide6.QtGui import QPainter, QBrush, QPolygon, QFont, QColor, QTextOption
from client.viewmodels.bubble_viewmodel import BubbleViewModel

class BubbleView(QWidget):
    """Виджет пузырька с сообщением"""
    
    bubble_shown = Signal()
    bubble_hidden = Signal()
    text_updated = Signal(str)
    
    def __init__(self, viewmodel: BubbleViewModel):
        super().__init__()
        self._vm = viewmodel
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Состояние
        self._character_pos = QPoint(0, 0)
        

        self._m_char_timer = QTimer()
        self._m_full_text = ""
        self._m_current_char = 0
        self._m_char_timer_int = 50

        self._anim_progress = 0.0
        self._animating = True
        self._anim_reverse = False
        self._hold_timer = QTimer()
        
        self._m_pos = "left-bottom"
        self._anim_timer = None
        self._m_char_timer_int = 1
        self._streaming_mode = False  
        self._text_edit = QTextEdit(self)
        self._text_edit.setReadOnly(True)
        self._text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._text_edit.setFrameShape(QTextEdit.Shape.NoFrame)
        self._text_edit.setFont(QFont("Segoe UI", 12))
        self._text_edit.setWordWrapMode(QTextOption.WrapMode.WordWrap)
        self._text_edit.setStyleSheet("""
            QTextEdit {
                background: transparent;
                color: #1a1a1a;
                border: none;
                padding: 5px;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 8px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: rgba(0, 0, 0, 30);
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0;
            }
        """)
        
        self.setFixedSize(300, 180)

        self.bubble_rect = QRect()
        self.wake_up_text_array = [
            "All ears!",
            "Ah? Yes, I'm listening...",
            "What task lies before me?",
            "Ready to work and communicate with you."
        ]
        
        self._m_char_timer.timeout.connect(self._print_next_char)
        self._hold_timer.timeout.connect(self._on_hold_timeout)
        self._vm.visibility_changed.connect(self._on_visibility_changed)
        self._vm.text_changed.connect(self._on_text_changed)
        self._vm.position_changed.connect(self._on_position_changed)
        self.setVisible(False)

    def _on_text_changed(self, text: str):
        """Обработка изменения текста из ViewModel"""
        if not text and self._m_full_text:
            return
        if text == self._m_full_text:
            return
        
        if not self._m_full_text:
            self._set_text(text)
        else:
            self._m_full_text = text
            self._text_edit.setPlainText(text)
            sb = self._text_edit.verticalScrollBar()
            sb.setValue(sb.maximum())
            self._m_current_char = len(text)

    
    def _set_text_silent(self, text: str):
        """Установка текста с анимацией печати (без повторной анимации появления)"""
        self._m_full_text = text
        self._m_current_char = len(self._text_edit.toPlainText())
        self._m_char_timer.start(self._m_char_timer_int)
    
    def _print_next_char(self):
        """Печать следующего символа"""
        if self._m_current_char < len(self._m_full_text):
            chars_to_print = 10 if self._streaming_mode else 1
            self._m_current_char = min(self._m_current_char + chars_to_print, len(self._m_full_text))
            
            current_text = self._m_full_text[:self._m_current_char]
            self._text_edit.setPlainText(current_text)
            
            sb = self._text_edit.verticalScrollBar()
            sb.setValue(sb.maximum())
        else:
            self._m_char_timer.stop()
            if self._m_current_char >= len(self._m_full_text):
                self._streaming_mode = False

    def set_character_pos(self, pos: QPoint):
        """Установка позиции персонажа"""
        self._character_pos = pos
    
    def show_random_wake_text(self):
        """Показать случайное приветственное сообщение"""
        random_text = self.wake_up_text_array[random.randint(0, len(self.wake_up_text_array) - 1)]
        self._set_text(random_text)
    
    def hide_with_delay(self, delay_ms: int):
        """Скрыть через задержку"""
        if self._hold_timer.isActive():
            self._hold_timer.stop()
        self._hold_timer.singleShot(delay_ms, self._animate_to_tail)

    def _on_position_changed(self, pos: str):
        """Обработка изменения позиции"""
        self._m_pos = pos
        self.update()

    def _on_visibility_changed(self, visible: bool):
        """Обработка изменения видимости"""
        if visible:
            if not self.isVisible():
                self._animate_from_tail()
        else:
            self._animate_to_tail()

    
    def _set_text(self, text: str):
        """Установка текста с анимацией появления"""
        if self._hold_timer.isActive():
            self._hold_timer.stop()
        
        self._animate_from_tail()
        self._m_full_text = text
        self._m_current_char = 0
        self._text_edit.clear()
        
        if self._streaming_mode:
            initial = text[:100]
            self._text_edit.setPlainText(initial)
            self._m_current_char = len(initial)
        
        self._m_char_timer.start(self._m_char_timer_int)

    
    def _on_hold_timeout(self):
        """Таймаут удержания"""
        self._animate_to_tail()
    
    def _animate_from_tail(self):
        """Анимация появления"""
        if self._anim_progress != 1.0:
            self._anim_progress = 0.0
            self._animating = True
            self._anim_reverse = False
            self.show()
            self.raise_()
            self._start_animation(20)
            self.bubble_shown.emit()
    
    def _animate_to_tail(self):
        """Анимация исчезновения"""
        if self._anim_progress != 0.0:
            self._anim_progress = 1.0
            self._animating = True
            self._anim_reverse = True
            self._start_animation(20)
            self.bubble_hidden.emit()
    
    def _start_animation(self, frequency: int):
        """Запуск анимации"""
        if self._anim_timer:
            self._anim_timer.stop()
        self._anim_timer = QTimer()
        self._anim_timer.timeout.connect(self._update_animation)
        self._anim_timer.start(frequency)
    
    def _update_animation(self):
        """Обновление анимации"""
        if not self._anim_reverse:
            if self._anim_progress < 1.0:
                self._anim_progress += 0.05
            else:
                self._anim_progress = 1.0
                self._animating = False
                if self._anim_timer:
                    self._anim_timer.stop()
        else:
            if self._anim_progress > 0.0:
                self._anim_progress -= 0.05
            else:
                self._anim_progress = 0.0
                self._animating = False
                if self._anim_timer:
                    self._anim_timer.stop()
                self.hide()
        
        self.update()
    
    def _create_bubble_tail(self, is_right: bool, is_top: bool) -> QPolygon:
        """Создание хвостика пузырька"""
        x_base = self.bubble_rect.right() if is_right else self.bubble_rect.left()
        y_base = self.bubble_rect.top() if is_top else self.bubble_rect.bottom()
        
        x_sign = -1 if is_right else 1
        y_sign = -1 if is_top else 1
        tail_len = 20
        if self._animating:
            tail_len = int(20 * self._anim_progress)
            if tail_len < 2:
                tail_len = 2
        
        return QPolygon([
            QPoint(x_base + x_sign * tail_len, y_base),
            QPoint(x_base + x_sign * tail_len // 2, y_base - y_sign * 8),
            QPoint(x_base, y_base + y_sign * tail_len)
        ])

    def _calculate_bubble_rect(self) -> QRect:
        """Расчет прямоугольника пузырька с учетом хвостика"""
        tail_size = 20
        margin = 15
        
        x = margin
        y = margin
        w = self.width() - margin * 2
        h = self.height() - margin * 2
    
        pos = self._vm.position  
        
        if not pos:
            pos = "left-bottom"  
        
        if "left" in pos: #type: ignore
            x += tail_size
            w -= tail_size
        else:
            w -= tail_size
        
        if "top" in pos: #type: ignore
            y += tail_size
            h -= tail_size
        else:
            h -= tail_size
        
        if self._animating:
            progress = self._anim_progress
            anchor_x = x
            anchor_y = y
            
            if "left" in pos: #type: ignore
                pass
            else:
                anchor_x = x + w
                x = anchor_x - w * progress
            
            w = w * progress
            
            if "top" in pos: #type: ignore
                pass
            else:
                anchor_y = y + h
                y = anchor_y - h * progress
            
            h = h * progress
            
            if w < 20:
                w = 20
            if h < 20:
                h = 20
        
        return QRect(int(x), int(y), int(w), int(h))

    def paintEvent(self, event):
        """Отрисовка пузырька"""
        painter = QPainter(self)
        
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Рисуем прозрачный фон
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
            painter.fillRect(self.rect(), Qt.GlobalColor.transparent)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            
            # Вычисляем прямоугольник пузырька
            self.bubble_rect = self._calculate_bubble_rect()
            
            # Получаем позицию
            pos = self._vm.position or "left-bottom"
            is_right = "right" in pos #type: ignore
            is_top = "top" in pos #type: ignore

            tail = self._create_bubble_tail(is_right, is_top)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, 15))
            shadow_rect = QRect(
                self.bubble_rect.x(),
                self.bubble_rect.y() + 2,
                self.bubble_rect.width(),
                self.bubble_rect.height()
            )
            painter.drawRoundedRect(shadow_rect, 14, 14)
            painter.setBrush(QColor(255, 255, 255, 248))
            painter.drawRoundedRect(self.bubble_rect, 14, 14)

            if not self._animating or self._anim_progress > 0.15:
                painter.drawPolygon(tail)
            
            text_margin = 12
            self._text_edit.setGeometry(
                self.bubble_rect.x() + text_margin,
                self.bubble_rect.y() + text_margin,
                max(0, self.bubble_rect.width() - text_margin * 2),
                max(0, self.bubble_rect.height() - text_margin * 2)
            )
        except Exception as e:
            print(f"Paint error: {e}")
        finally:
            painter.end()
    
    def hideEvent(self, event):
        """Виджет скрыт"""
        if self._anim_timer:
            self._anim_timer.stop()
        self._anim_timer = None
        self._streaming_mode = False
        self._m_full_text = ""
        self._m_current_char = 0
        self._text_edit.clear()
        self._m_char_timer.stop()
        
        super().hideEvent(event)