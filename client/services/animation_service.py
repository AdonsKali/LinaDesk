from pathlib import Path
from typing import Dict, Optional
from PySide6.QtGui import QMovie
from PySide6.QtCore import QObject
import logging

logger = logging.getLogger(__name__)


class AnimationService(QObject):
    """Сервис для работы с анимациями (WebP, GIF)"""
    
    def __init__(self, assets_path: str = "client/assets/animations"):
        super().__init__()
        self._assets_path = Path(assets_path)
        self._cache: Dict[str, QMovie] = {}
        self._current_animation: Optional[str] = None
        
        self._assets_path.mkdir(parents=True, exist_ok=True)
        print(f"AnimationService initialized, path: {self._assets_path}")
    
    def get_animation(self, name: str) -> Optional[QMovie]:
        """Получить анимацию (WebP приоритет, затем GIF)"""
        if name not in self._cache:
            webp_path = self._assets_path / f"{name}.webp"
            gif_path = self._assets_path / f"{name}.gif"
            
            movie = None
            if webp_path.exists():
                movie = QMovie(str(webp_path))
                movie.setCacheMode(QMovie.CacheMode.CacheAll)
                print(f"Loaded WebP: {name}")
            elif gif_path.exists():
                movie = QMovie(str(gif_path))
                movie.setCacheMode(QMovie.CacheMode.CacheAll)
                print(f"Loaded GIF: {name}")
            else:
                print(f"Animation not found: {name}")
                return None
            
            self._cache[name] = movie
        
        movie = self._cache.get(name)
        if movie:
            if self._current_animation != name:
                if self._current_animation and self._cache.get(self._current_animation):
                    self._cache[self._current_animation].stop()
                
                movie.stop()
                movie.start()
                self._current_animation = name
        return movie
    
    def preload(self, names: list[str]):
        """Предзагрузка анимаций"""
        for name in names:
            self.get_animation(name)