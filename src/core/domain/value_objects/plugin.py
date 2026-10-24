from dataclasses import dataclass
from src.core.domain.value_objects.tool import Tool


@dataclass(frozen=True)
class Plugin:
    """Value Object для плагинов - доменный объект значения"""
    name: str
    version: str
    tools: list[Tool]
    config: dict
    enabled: bool

    def __post_init__(self):
        # Валидация на уровне доменного объекта
        if not self.name:
            raise ValueError("Plugin name cannot be empty")
        if not self.version:
            raise ValueError("Plugin version cannot be empty")
        if self.config is None:
            raise ValueError("Plugin config cannot be empty")
        
    def __str__(self) -> str:
        return f"Plugin(name={self.name}, version={self.version}, enabled={self.enabled})"     
        
    def to_dict(self) -> dict:
        """Convert Plugin to dictionary representation."""
        return {
            "name": self.name,
            "version": self.version,
            "tools": self.tools,
            "config": self.config,
            "enabled": self.enabled
        }