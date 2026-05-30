from typing import Tuple
from PySide6.QtCore import QObject
from client.core.event_bus import EventBus
from client.core.events import Event
from client.core.event_types import EventType
from utils.logger import logger

log = logger.get(__name__)

class PositionService(QObject):
    """Сервис позиционирования UI элементов"""
    
    def __init__(self, event_bus: EventBus):
        super().__init__()
        self._event_bus = event_bus
        self._screen_width = 1920
        self._screen_height = 1080
        self._chibi_width = 200
        self._chibi_height = 200
        self._bubble_width = 320
        self._bubble_height = 200
        self._chat_width = 350
        self._chat_height = 60
        self._statuses_width = 50
        self._statuses_height = 200
        
        self._bubble_margin = -35   
        self._chat_margin = 5 
        self._statuses_margin = -5
    
    def set_screen_size(self, width: int, height: int):
        self._screen_width = width
        self._screen_height = height
    
    def set_widget_sizes(self, chibi_w: int, chibi_h: int, 
                         bubble_w: int, bubble_h: int,
                         chat_w: int, chat_h: int):
        self._chibi_width = chibi_w
        self._chibi_height = chibi_h
        self._bubble_width = bubble_w
        self._bubble_height = bubble_h
        self._chat_width = chat_w
        self._chat_height = chat_h
    
    def calculate_bubble_position(self, chibi_x: int, chibi_y: int) -> Tuple[int, int, str]:
        """Расчет позиции облачка относительно чиби"""
        space_right = self._screen_width - (chibi_x + self._chibi_width) - self._bubble_margin
        space_left = chibi_x - self._bubble_margin
        
        if space_right >= self._bubble_width:
            bubble_x = chibi_x + self._chibi_width + self._bubble_margin - 20
            tail_horizontal = "left"
        elif space_left >= self._bubble_width:
            bubble_x = chibi_x - self._bubble_width - self._bubble_margin - 20
            tail_horizontal = "right"
        else:
            if space_right > space_left:
                bubble_x = self._screen_width - self._bubble_width - 20
                tail_horizontal = "left"
            else:
                bubble_x = 0
                tail_horizontal = "right"
        
        space_above = chibi_y - self._bubble_margin
        space_below = self._screen_height - (chibi_y + self._chibi_height) - self._bubble_margin
        
        if space_above >= self._bubble_height:
            bubble_y = chibi_y - self._bubble_height - self._bubble_margin + 20
            tail_vertical = "bottom"
        elif space_below >= self._bubble_height:
            bubble_y = chibi_y + self._chibi_height + self._bubble_margin + 20
            tail_vertical = "top"
        else:
            if space_above > space_below:
                bubble_y = 0
                tail_vertical = "bottom"
            else:
                bubble_y = self._screen_height - self._bubble_height + 20
                tail_vertical = "top"
        
        # Корректировка
        bubble_x = max(0, min(bubble_x, self._screen_width - self._bubble_width))
        bubble_y = max(0, min(bubble_y, self._screen_height - self._bubble_height))
        log.debug(f"Bubble position: {bubble_x}, {bubble_y}")
        
        position_type = f"{tail_horizontal}-{tail_vertical}"
        
        return int(bubble_x), int(bubble_y), position_type
    
    def calculate_chat_position(self, chibi_x: int, chibi_y: int) -> Tuple[int, int]:
        """Расчет позиции чата"""
        chat_x = chibi_x
    
        if chibi_y + self._chibi_height + self._chat_height + self._chat_margin < self._screen_height:
            chat_y = chibi_y + self._chibi_height + self._chat_margin
        else:
            chat_y = chibi_y - self._chat_height - self._chat_margin

        chat_x = max(0, min(chat_x, self._screen_width - self._chat_width))
        chat_y = max(0, min(chat_y, self._screen_height - self._chat_height))
        log.debug(f"Chat position: {chat_x}, {chat_y}")
        
        return int(chat_x), int(chat_y)
    
    def calculate_statuses_position(self, chibi_x: int, chibi_y: int):
        """Calculate statuses position - always try left first, if not enough space - place right"""
        statuses_y = chibi_y
        statuses_x = chibi_x - self._statuses_width - self._statuses_margin

        if statuses_x < 0:
            statuses_x = chibi_x + self._chibi_width + self._statuses_margin
            if statuses_x + self._statuses_width > self._screen_width:
                statuses_x = chibi_x + (self._chibi_width // 2) - (self._statuses_width // 2)
                statuses_x = max(0, min(statuses_x, self._screen_width - self._statuses_width))
        
        statuses_y = max(0, min(statuses_y, self._screen_height - self._statuses_height))
        log.debug(f"Statuses position: {statuses_x}, {statuses_y}")
        
        return int(statuses_x), int(statuses_y)
    
    def on_chibi_moved(self, x: int, y: int):
        """Обработка перемещения чиби"""
        bubble_x, bubble_y, position_type = self.calculate_bubble_position(x, y)
        chat_x, chat_y = self.calculate_chat_position(x, y)
        statuses_x, statuses_y = self.calculate_statuses_position(x, y)
        self._event_bus.emit(Event(
            EventType.BUBBLE_POSITION_UPDATED,
            {'x': int(bubble_x), 'y': int(bubble_y), 'type': position_type}
        ))
        self._event_bus.emit(Event(
            EventType.CHAT_POSITION_UPDATED,
            {'x': int(chat_x), 'y': int(chat_y)}
        ))
        self._event_bus.emit(Event(
            EventType.STATUSES_POSITION_UPDATED,
            {'x': int(statuses_x), 'y': int(statuses_y)}
        ))
        log.debug(f"Cibi position: {position_type} ({x}, {y})")