from abc import ABC, abstractmethod
from src.core.domain.value_objects.plugin import Plugin


class PluginLoaderPort(ABC):
    """Загрузка плагинов из внешних источников."""

    @abstractmethod
    async def get_enabled_plugins(self) -> list[Plugin]: ...

    @abstractmethod
    async def get_plugin(self, name: str) -> Plugin | None: ...