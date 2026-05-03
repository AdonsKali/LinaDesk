from pathlib import Path
from typing import Dict, Optional
from PySide6.QtGui import QMovie
from client.models.chibi_model import AnimationType
from client.core.event_bus import EventBus
from .base_service import BaseService

class AnimationService(BaseService):
    """Сервис анимаций персонажа"""
    def __init__(self, event_bus: EventBus, assets_path: str = "client/assets/animations"):
        super().__init__(event_bus)
        self._assets_path = Path(assets_path)
        self._cache: Dict[str, QMovie] = {}
        self._current: Optional[str] = None
        
    def initialize(self) -> None:
        """Предзагрузка анимаций"""
        animations = [a.value for a in AnimationType]
        for name in animations:
            self._load_animation(name)
    
    def _load_animation(self, name: str) -> Optional[QMovie]:
        """Загрузка анимации в кеш"""
        if name in self._cache:
            return self._cache[name]
        
        for ext in ['.webp', '.gif']:
            path = self._assets_path / f"{name}{ext}"
            if path.exists():
                movie = QMovie(str(path))
                movie.setCacheMode(QMovie.CacheMode.CacheAll)
                self._cache[name] = movie
                return movie
        
        return None
    
    def play_animation(self, animation: AnimationType) -> Optional[QMovie]:
        """Воспроизведение анимации"""
        name = animation.value
        
        if self._current and self._current in self._cache:
            self._cache[self._current].stop()
        movie = self._load_animation(name)
        if movie:
            movie.start()
            self._current = name
        
        return movie
    
    def cleanup(self) -> None:
        """Очистка кеша анимаций"""
        for movie in self._cache.values():
            movie.stop()
        self._cache.clear()
