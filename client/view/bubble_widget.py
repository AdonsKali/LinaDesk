import random
from PySide6.QtWidgets import QTextEdit
from PySide6.QtCore import Qt, QPoint, QRect, QTimer, Signal
from PySide6.QtGui import QPainter, QBrush, QPolygon, QFont, QColor, QPaintEvent, QTextOption
from .base_widget import BaseWidget
from viewmodel.bubble_viewmodel import BubbleViewModel


class BubbleWidget(BaseWidget):
    """Виджет пузырька с сообщением - поддерживает анимации и ViewModel"""
    
    # Сигналы для внешнего управления
    bubble_shown = Signal()
    bubble_hidden = Signal()
    text_updated = Signal(str)
    
    def __init__(self, viewmodel: BubbleViewModel):
        super().__init__()
        self._vm = viewmodel
        
        # Состояние
        self._character_pos = QPoint(0, 0)
        
        # Текст и анимация печати
        self._m_char_timer: QTimer = QTimer()
        self._m_full_text: str = ""
        self._m_current_char: int = 0
        self._m_char_timer_int = 50
        
        # Анимация появления/исчезновения
        self._anim_progress: float = 0.0
        self._animating: bool = True
        self._anim_reverse: bool = False
        self._hold_timer = QTimer()
        
        # Переменная для позиции пузырька
        self._m_pos = "left-bottom"

        # Таймер для анимации
        self.animation_delay = None
        
        # Текстовое поле
        self._text_edit = QTextEdit(self)
        self._text_edit.setReadOnly(True)
        self._text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._text_edit.setFrameShape(QTextEdit.Shape.NoFrame)
        self._text_edit.setFont(QFont("Arial", 12))
        self._text_edit.setWordWrapMode(QTextOption.WrapMode.WordWrap)
        self._text_edit.setStyleSheet("""
            QTextEdit {
                background: transparent;
                color: black;
                border: none;
                border-radius: 12px;
                padding: 10px;
            }
        """)
        
        # Размер пузырька
        self.setFixedSize(280, 150)
        
        # Приветственные тексты
        self.wake_up_text_array = [
            "All ears!",
            "Ah? Yes, I'm listening...",
            "What task lies before me?",
            "Ready to work and communicate with you."
        ]
        
        self.bubble_rect = QRect()
        
        # Подключаем таймеры
        self._m_char_timer.timeout.connect(self._print_next_char)
        self._hold_timer.timeout.connect(self._on_hold_timeout)
        
        # Подписка на ViewModel
        self._vm.visibility_changed.connect(self._on_visibility_changed)
        self._vm.text_changed.connect(self._on_text_changed)
        self._vm.position_changed.connect(self._on_position_changed)  # Added position subscription
        
        # Начальное состояние
        self.setVisible(False)

    def set_character_pos(self, pos: QPoint):
        """Установка позиции персонажа (для внешнего позиционирования)"""
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
        """Обработка изменения позиции из ViewModel"""
        self._m_pos = pos
        self.update()

    def _on_visibility_changed(self, visible: bool):
        """Обработка изменения видимости из ViewModel"""
        if visible:
            if not self.isVisible():  # Only animate if not already visible
                self._animate_from_tail()
        else:
            self._animate_to_tail()
    
    def _on_text_changed(self, text: str):
        """Обработка изменения текста из ViewModel"""
        # Check if this is the first time setting the text
        if self._m_full_text == "":
            # First time - start animation
            self._set_text(text)
        else:
            # Update existing text without restarting animation
            self._m_full_text = text
            # Update the text edit if we're still animating
            if self._m_char_timer.isActive():
                # Continue animation with updated full text
                pass
            else:
                # Animation is done, just update the text
                self._text_edit.setPlainText(text)
                sb = self._text_edit.verticalScrollBar()
                sb.setValue(sb.maximum())
    
    def _set_text(self, text: str):
        """Установка текста с анимацией печати"""
        if self._hold_timer.isActive():
            self._hold_timer.stop()
        
        self._animate_from_tail()
        self._m_full_text = text
        self._m_current_char = 0
        self._text_edit.clear()
        self._m_char_timer.start(self._m_char_timer_int)
    
    def _print_next_char(self):
        """Печать следующего символа"""
        # Check if we have more characters to print from the current full text
        if self._m_current_char < len(self._m_full_text):
            # Update the text edit with the next character
            current_text = self._m_full_text[:self._m_current_char+1]
            self._text_edit.setPlainText(current_text)
            self._m_current_char += 1
            
            sb = self._text_edit.verticalScrollBar()
            sb.setValue(sb.maximum())
        else:
            # We've reached the end of the current full text
            self._m_char_timer.stop()
    
    def _on_hold_timeout(self):
        """Таймаут удержания"""
        self._animate_to_tail()
    
    def _animate_from_tail(self):
        """Анимация появления"""
        if self._anim_progress != 1.0:
            self._anim_progress = 0.0
            self._anim_reverse = False
            self.show()
            
            self._start_animation(20)
            self.bubble_shown.emit()
    
    def _animate_to_tail(self):
        """Анимация исчезновения"""
        if self._anim_progress != 0.0:
            self._anim_progress = 1.0
            self._anim_reverse = True
            self._start_animation(20)
            self.bubble_hidden.emit()
    
    def _start_animation(self, frequency: int):
        """Запуск анимации"""
        if self.animation_delay:
            self.animation_delay.stop()
        self.animation_delay = QTimer()
        self.animation_delay.timeout.connect(self._update_animation)
        self.animation_delay.start(frequency)
    
    def _update_animation(self):
        """Обновление анимации"""
        if not self._anim_reverse:
            if self._anim_progress < 1.0:
                self._anim_progress += 0.05
            else:
                self._anim_progress = 1.0
                if self.animation_delay:
                    self.animation_delay.stop()
        else:
            if self._anim_progress > 0.0:
                self._anim_progress -= 0.05
            else:
                self._anim_progress = 0.0
                if self.animation_delay:
                    self.animation_delay.stop()
                self.hide()
        
        self.update()
    
    def _create_bubble_tail(self, is_right: bool, is_top: bool) -> QPolygon:
        """Создание хвостика пузырька"""
        x_base = self.bubble_rect.right() if is_right else self.bubble_rect.left()
        y_base = self.bubble_rect.top() if is_top else self.bubble_rect.bottom()
        
        x_sign = -1 if is_right else 1
        y_sign = -1 if is_top else 1
        
        if self._animating and (self._anim_progress == 1.0 or self._anim_progress == 0.0):
            return QPolygon([
                QPoint(int(x_base + x_sign * 20 * self._anim_progress), y_base),
                QPoint(int(x_base + x_sign * 10 * self._anim_progress), y_base),
                QPoint(int(x_base - x_sign * 10 * self._anim_progress), y_base + y_sign * 20)
            ])
        
        return QPolygon([
            QPoint(x_base + x_sign * 20, y_base),
            QPoint(x_base + x_sign * 10, y_base),
            QPoint(x_base - x_sign * 10, y_base + y_sign * 20)
        ])

    def paintEvent(self, event):
        """Отрисовка пузырька"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(255, 255, 255, 240)))
        
        full_rect = QRect(10, 10, self.width() - 20, self.height() - 30)
        
        # Определяем параметры хвостика в зависимости от позиции
        pos = self._vm.position  # Get position from ViewModel
        match pos:
            case "left-top":
                tail_points = self._create_bubble_tail(False, True)
                tail_point = QPoint(full_rect.left(), full_rect.top())
            case "left-bottom":
                tail_points = self._create_bubble_tail(False, False)
                tail_point = QPoint(full_rect.left(), full_rect.bottom())
            case "right-bottom":
                tail_points = self._create_bubble_tail(True, False)
                tail_point = QPoint(full_rect.right(), full_rect.bottom())
            case "right-top":
                tail_points = self._create_bubble_tail(True, True)
                tail_point = QPoint(full_rect.right(), full_rect.top())
            case _:
                tail_points = self._create_bubble_tail(False, False)
                tail_point = QPoint(full_rect.left(), full_rect.bottom())
        
        if self._animating:
            w = full_rect.width() * self._anim_progress
            h = full_rect.height() * self._anim_progress
            
            # Вычисляем позицию в зависимости от типа анимации
            match self._m_pos:
                case "left-top":
                    x = tail_point.x()
                    y = tail_point.y()
                case "left-bottom":
                    x = tail_point.x()
                    y = tail_point.y() - h
                case "right-bottom":
                    x = tail_point.x() - w
                    y = tail_point.y() - h
                case "right-top":
                    x = tail_point.x() - w
                    y = tail_point.y()
                case _:
                    x = tail_point.x()
                    y = tail_point.y() - h
            
            self.bubble_rect = QRect(int(x), int(y), int(w), int(h))
            
            # Выбираем правильный хвостик
            match pos:
                case "left-top":
                    tail = self._create_bubble_tail(False, True)
                case "left-bottom":
                    tail = self._create_bubble_tail(False, False)
                case "right-bottom":
                    tail = self._create_bubble_tail(True, False)
                case "right-top":
                    tail = self._create_bubble_tail(True, True)
                case _:
                    tail = self._create_bubble_tail(False, False)
        else:
            self.bubble_rect = full_rect
            tail = tail_points
        
        # Рисуем пузырек
        painter.drawRoundedRect(self.bubble_rect, 12, 12)
        painter.drawPolygon(tail)
        
        # Обновляем геометрию текстового поля
        text_margin = 10
        self._text_edit.setGeometry(
            self.bubble_rect.x() + text_margin,
            self.bubble_rect.y() + text_margin,
            self.bubble_rect.width() - text_margin * 2,
            self.bubble_rect.height() - text_margin * 2
        )
        
        painter.end()
    
    def resizeEvent(self, event):
        """Обработка изменения размера"""
        text_margin = 10
        self._text_edit.setGeometry(
            text_margin,
            text_margin,
            self.width() - text_margin * 2,
            self.height() - text_margin * 2
        )
    
    def showEvent(self, event):
        """Виджет показан"""
        super().showEvent(event)
    
    def hideEvent(self, event):
        """Виджет скрыт"""
        if self.animation_delay:
            self.animation_delay.stop()
        super().hideEvent(event)