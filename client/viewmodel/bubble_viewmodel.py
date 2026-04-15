from PySide6.QtCore import QObject, Signal, Property
from core.event_bus import EventBus, Event, EventType


class BubbleViewModel(QObject):
    visibility_changed = Signal(bool)
    text_changed = Signal(str)
    position_changed = Signal(str)  # left-top, left-bottom, right-top, right-bottom
    
    def __init__(self, event_bus: EventBus):
        super().__init__()
        self._event_bus = event_bus
        self._is_visible = False
        self._text = ""
        self._position = "left-bottom"  # default position
        self._updating = False  # recursion protection
        
        # Subscribe to events
        event_bus.subscribe(EventType.UI_SHOW_MESSAGE, self._on_show)
        event_bus.subscribe(EventType.UI_HIDE_MESSAGE, self._on_hide)
    
    @Property(bool, notify=visibility_changed)
    def is_visible(self) -> bool:
        return self._is_visible
    
    @Property(str, notify=text_changed)
    def text(self) -> str:
        return self._text
    
    @Property(str, notify=position_changed)
    def position(self) -> str:
        return self._position
    
    def set_position(self, pos: str):
        """Set bubble position (left-top, left-bottom, right-top, right-bottom)"""
        if self._position != pos:
            self._position = pos
            self.position_changed.emit(self._position)
    
    def hide(self):
        """Hide message bubble"""
        self._event_bus.emit(Event(EventType.UI_HIDE_MESSAGE))
    
    def _on_show(self, event: Event):
        """Show message bubble"""
        if self._updating:
            return
        
        self._updating = True
        try:
            if not self._is_visible:
                self._is_visible = True
                self.visibility_changed.emit(True)
            
            new_text = event.data or ""
            if self._text != new_text:
                self._text = new_text
                self.text_changed.emit(self._text)
        finally:
            self._updating = False
    
    def _on_hide(self, event: Event):
        """Hide message bubble"""
        if self._updating:
            return
        
        self._updating = True
        try:
            if self._is_visible:
                self._is_visible = False
                self._text = ""
                self.visibility_changed.emit(False)
                self.text_changed.emit("")
        finally:
            self._updating = False