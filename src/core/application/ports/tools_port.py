from typing import Any, Callable, Protocol, Sequence
from src.core.domain.value_objects.tool import ToolSpec


ToolHandler = Callable[..., Any]


class ToolRegistryPort(Protocol):
    """Реестр доступных инструментов. Реализация — infrastructure."""

    async def get_available(self) -> Sequence[ToolSpec]:
        """Возвращает все доступные инструменты."""
        ...

    async def get_spec(self, name: str) -> ToolSpec | None:
        """Возвращает spec по имени."""
        ...

    async def get_handler(self, name: str) -> ToolHandler | None:
        """Возвращает handler по имени."""
        ...