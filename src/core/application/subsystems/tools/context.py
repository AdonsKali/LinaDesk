from dataclasses import dataclass, field

from src.core.domain.value_objects.tool import ToolSpec
from src.core.domain.value_objects.tool import ToolPermission


@dataclass(frozen=True)
class ToolContext:
    """
    Состояние tools-подсистемы на текущий запрос.
    """
    available_tools: list[ToolSpec] = field(default_factory=list)
    user_permissions: frozenset[ToolPermission] = frozenset()

    def has_tool(self, name: str) -> bool:
        return any(t.name == name for t in self.available_tools)

    def get_spec(self, name: str) -> ToolSpec | None:
        for t in self.available_tools:
            if t.name == name:
                return t
        return None