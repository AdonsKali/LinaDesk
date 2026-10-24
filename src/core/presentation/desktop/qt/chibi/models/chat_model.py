from dataclasses import dataclass
from enum import Enum
from typing import Dict, List

class ChatPosition(Enum):
    UNDER = "under"
    ABOVE = "above"


@dataclass
class MiniChatModel:
    """Модель чата"""
    def __init__(self) -> None:
        self._is_visible: bool = False
        self._is_processing: bool = False
        self._is_recording: bool = False
        self._has_focus: bool = False
        self._position: ChatPosition = ChatPosition.UNDER
        self._input_text: str = ""
        self._data_files: List[Dict] = []


    def clear_data_files(self) -> None:
        self._data_files.clear()
    def add_data_files(self, data: dict) -> None:
        self._data_files.append(data)
    @property
    def is_visible(self) -> bool:
        return self._is_visible
    
    @is_visible.setter
    def is_visible(self, value: bool) -> None:
        self._is_visible = value
    
    @property
    def position(self) -> ChatPosition:
        return self._position
    
    @position.setter
    def position(self, value: ChatPosition) -> None:
        self._position = value
    
    @property
    def is_processing(self) -> bool:
        return self._is_processing
    
    @is_processing.setter
    def is_processing(self, value: bool) -> None:
        self._is_processing = value
    
    @property
    def has_focus(self) -> bool:
        return self._has_focus
    
    @has_focus.setter
    def has_focus(self, has_focus: bool) -> None:
        self._has_focus = has_focus
    
    @property
    def is_recording(self) -> bool:
        return self._is_recording
    
    @is_recording.setter
    def is_recording(self, is_recording: bool) -> None:
        self._is_recording = is_recording
    
    @property
    def input_text(self) -> str:
        return self._input_text
    
    @input_text.setter
    def input_text(self, text: str, ) -> None:
        self._input_text = text
    