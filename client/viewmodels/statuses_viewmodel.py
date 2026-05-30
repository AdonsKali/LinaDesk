from client.models.chibi_model import AnimationType
from client.viewmodels.base_viewmodel import BaseViewModel
from client.core.events import Event
from client.core.event_types import EventType
from client.models.statuses_model import StatusesModel, StatusType
from PySide6.QtCore import Signal
from pathlib import Path

class StatusesViewModel(BaseViewModel):
    """ViewModel для управления статусами чиби"""
    
    statuses_updated = Signal()
    position_changed = Signal(int, int)
    
    def __init__(self, event_bus):
        super().__init__(event_bus)
        self._model = StatusesModel()
        
        self.subscribe(EventType.USER_FILE_DROPPED, self._on_file_dropped)
        self.subscribe(EventType.STATUSES_POSITION_UPDATED, self._on_position_changed)
        self.subscribe(EventType.CLEAR_ALL_FILE_STATUSES, self.clear_all_file_statuses)
    
    def _on_file_dropped(self, event: Event) -> None:
        """Файл перетащен на чиби - добавляем новый статус"""
        file_path = event.data
        file_name = Path(file_path).name
        
        # Получаем тип и иконку для файла
        status_type, emoji = self._model.get_file_info(file_path)
        
        # Проверяем лимит
        if len(self._model.statuses) >= self._model.max_statuses:
            self.emit(Event(EventType.BUBBLE_TEXT_CHANGED, "I'm sorry, but I can't add more..."))
            self.emit(Event(EventType.CHIBI_ANIMATION_CHANGED, AnimationType.TALK.value))
            return
        
        # Добавляем статус
        status = self._model.add_status(
            status_type=status_type,
            icon_path=emoji,
            text=f"{status_type.name}: {file_name}",
            data={"file_path": file_path, "file_name": file_name}
        )
        
        if status:
            self.emit(Event(EventType.ADD_TEXT_TO_PROMPT, {file_path: status_type.name}))
            self.statuses_updated.emit()
    
    def remove_file_status(self, file_path: str) -> None:
        """Удаление статуса конкретного файла"""
        self._model.remove_file_status_by_path(file_path)
        self.statuses_updated.emit()
    
    def get_statuses(self):
        return self._model.get_statuses()
    
    def clear_all_file_statuses(self, event: Event) -> None:
        """Очистка всех файловых статусов"""
        self._model.clear_all()
        self.statuses_updated.emit()
    
    def _on_position_changed(self, event: Event):
        """Обработка изменения позиции"""
        data = event.data
        self.position_changed.emit(data['x'], data['y'])