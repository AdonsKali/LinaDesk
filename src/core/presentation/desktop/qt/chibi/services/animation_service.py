from pathlib import Path
from typing import Dict, Optional
from PySide6.QtGui import QMovie
from ..models.chibi_model import AnimationType
from ..core.event_bus import EventBus
from .base_service import BaseService
import logging

log = logging.getLogger(__name__)

class AnimationService(BaseService):
    """Сервис анимаций персонажа"""
    def __init__(self, event_bus: EventBus, assets_path: str = "src/resources/animations"):
        super().__init__(event_bus)
        self._assets_path = Path(assets_path)
        self._cache: Dict[str, QMovie] = {}
        self._current: Optional[str] = None
        self._is_cleaned = False
        
    def initialize(self) -> None:
        """Предзагрузка анимаций"""
        animations = [a.value for a in AnimationType]
        for name in animations:
            self._load_animation(name)
    
    def _load_animation(self, name: str) -> Optional[QMovie]:
        """Загрузка анимации в кеш"""
        if name in self._cache:
            movie = self._cache[name]
            if movie:
                movie.stop()
                movie.start()
            return movie
        
        for ext in ['.webp', '.gif']:
            path = self._assets_path / f"{name}{ext}"
            if path.exists():
                movie = QMovie(str(path), parent=self)
                # Важно: используем CacheNone чтобы не хранить все кадры в памяти
                movie.setCacheMode(QMovie.CacheMode.CacheNone)
                self._cache[name] = movie
                return movie
        
        return None
    
    def play_animation(self, animation: AnimationType) -> Optional[QMovie]:
        """Воспроизведение анимации"""
        name = animation.value
        
        if self._current and self._current in self._cache:
            current_movie = self._cache.get(self._current)
            if current_movie:
                current_movie.stop()
        
        movie = self._load_animation(name)
        if movie:
            movie.start()
            self._current = name
        
        return movie
    
    def cleanup(self) -> None:
        """Полная очистка кеша анимаций"""
        if self._is_cleaned:
            return
        
        self._is_cleaned = True
        log.info(f"Cleaning up AnimationService...")
        
        # Останавливаем и удаляем все анимации
        for key, movie in list(self._cache.items()):
            if movie:
                try:
                    movie.stop()
                    movie.blockSignals(True)
                    movie.deleteLater()
                except Exception as e:
                    log.error(f"Error deleting animation {key}: {e}")
        
        self._cache.clear()
        self._current = None
        
        # Принудительная очистка
        import gc
        gc.collect()
        
        log.info("AnimationService cleaned up")
