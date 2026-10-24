from abc import ABC, abstractmethod

from src.core.domain.value_objects.tool import Tool, ToolPermission


class BaseTool(ABC):
    """
    Базовый класс для built-in инструментов.
    """

    name: str = ""
    description: str = ""
    parameters: dict[str, str] = {}
    permissions: list[ToolPermission] = []

    @abstractmethod
    async def execute(self, **kwargs) -> str:
        ...

    def to_domain_tool(self) -> Tool:
        """Конвертация в domain Tool для регистрации в реестре."""
        return Tool(
            name=self.name,
            description=self.description,
            handler=self.execute,
            is_enabled=True,
            permissions=list(self.permissions),
            parameters=dict(self.parameters),
        )