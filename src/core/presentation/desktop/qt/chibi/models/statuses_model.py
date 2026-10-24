from typing import Any, List
from enum import Enum, auto
from dataclasses import dataclass

class StatusType(Enum):
    FILE = auto()      # Обычные файлы
    IMAGE = auto()     # Изображения
    AUDIO = auto()     # Аудио
    VIDEO = auto()     # Видео
    ARCHIVE = auto()   # Архивы

@dataclass
class Status:
    """Статус (бафф/эффект) чиби"""
    id: str
    type: StatusType
    icon_path: str  # эмодзи или путь к иконке
    text: str
    data: Any = None

class StatusesModel:
    """Модель для управления статусами чиби"""
    
    def __init__(self):
        self.statuses: List[Status] = []
        self.w: int = 50
        self.h: int = 200
        self.is_visible: bool = True
        self._max_statuses = 3
        self._next_id = 1

        # Карта расширений -> (StatusType, эмодзи)
        self._type_map = {
            # Изображения
            '.png': (StatusType.IMAGE, "🖼️"),
            '.jpg': (StatusType.IMAGE, "🖼️"),
            '.jpeg': (StatusType.IMAGE, "🖼️"),
            '.gif': (StatusType.IMAGE, "🖼️"),
            '.bmp': (StatusType.IMAGE, "🖼️"),
            '.webp': (StatusType.IMAGE, "🖼️"),
            
            # Аудио
            '.mp3': (StatusType.AUDIO, "🎵"),
            '.wav': (StatusType.AUDIO, "🎵"),
            '.ogg': (StatusType.AUDIO, "🎵"),
            '.flac': (StatusType.AUDIO, "🎵"),
            
            # Видео
            '.mp4': (StatusType.VIDEO, "🎬"),
            '.avi': (StatusType.VIDEO, "🎬"),
            '.mkv': (StatusType.VIDEO, "🎬"),
            '.mov': (StatusType.VIDEO, "🎬"),
            
            # Архивы
            '.zip': (StatusType.ARCHIVE, "📦"),
            '.rar': (StatusType.ARCHIVE, "📦"),
            '.7z': (StatusType.ARCHIVE, "📦"),
            '.tar': (StatusType.ARCHIVE, "📦"),
            
            # Документы (обычные файлы)
            '.txt': (StatusType.FILE, "📄"),
            '.pdf': (StatusType.FILE, "📑"),
            '.doc': (StatusType.FILE, "📝"),
            '.docx': (StatusType.FILE, "📝"),
            '.xls': (StatusType.FILE, "📊"),
            '.xlsx': (StatusType.FILE, "📊"),
            '.exe': (StatusType.FILE, "⚙️"),
        }
        
        self.DEFAULT_TYPE = (StatusType.FILE, "📄")
    
    @property
    def max_statuses(self) -> int:
        return self._max_statuses
    
    def get_file_info(self, file_path: str) -> tuple[StatusType, str]:
        """Получение типа статуса и иконки для файла"""
        from pathlib import Path
        ext = Path(file_path).suffix.lower()
        return self._type_map.get(ext, self.DEFAULT_TYPE)
    
    def _generate_id(self) -> str:
        """Генерация уникального ID"""
        id_str = str(self._next_id)
        self._next_id += 1
        return id_str
    
    def add_status(self, status_type: StatusType, icon_path: str, 
                   text: str, data: Any = None) -> Status | None:
        """Добавление нового статуса"""
        # Проверяем, нет ли уже такого файла
        for s in self.statuses:
            if s.data and s.data.get("file_path") == data.get("file_path"):
                return None
        
        status = Status(
            id=self._generate_id(),
            type=status_type,
            icon_path=icon_path,
            text=text,
            data=data
        )
        self.statuses.append(status)
        return status
    
    def remove_status(self, status_id: str) -> bool:
        """Удаление статуса по ID"""
        for i, status in enumerate(self.statuses):
            if status.id == status_id:
                self.statuses.pop(i)
                return True
        return False
    
    def remove_status_by_type(self, status_type: StatusType) -> None:
        """Удаление всех статусов определенного типа"""
        self.statuses = [s for s in self.statuses if s.type != status_type]
    
    def remove_file_status_by_path(self, file_path: str) -> None:
        """Удаление статуса файла по пути"""
        self.statuses = [s for s in self.statuses 
                        if not (s.data and s.data.get("file_path") == file_path)]
    
    def get_statuses(self) -> List[Status]:
        """Получение всех статусов"""
        return self.statuses.copy()
    
    def get_status_by_path(self, path: str):
        """Получение статуса по пути"""
        for status in self.statuses:
            if status.data and status.data.get("file_path") == path:
                return status
        return None
    
    def clear_all(self) -> None:
        """Очистка всех статусов"""
        self.statuses.clear()