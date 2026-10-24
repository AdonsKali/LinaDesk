from typing import Callable, Sequence
from src.core.domain.value_objects.tool import ToolSpec
from src.core.application.ports.tools_port import ToolRegistryPort
from src.core.domain.value_objects.tool import Tool
from src.core.utils.logger import logger
logger = logger.get(__name__)


class InMemoryToolRegistry(ToolRegistryPort):
    """
    In-memory реестр инструментов.
    """

    def __init__(self):
        self._specs: dict[str, ToolSpec] = {}
        self._handlers: dict[str, Callable] = {}

    def register_tool(self, tool: Tool, plugin_name: str = "builtin") -> None:
        """Регистрирует один Tool."""
        if tool.name in self._specs:
            raise ValueError(f"Duplicate tool: {tool.name}")
        if not tool.is_enabled:
            return
        spec = ToolSpec.from_tool(tool, plugin_name)
        self._specs[tool.name] = spec
        self._handlers[tool.name] = tool.handler
        logger.info(f"[ToolRegistry] registered: {tool.name}")

    def register_builtin(self, tool_class) -> None:
        """Регистрирует built-in tool (класс BaseTool)."""
        instance = tool_class()
        self.register_tool(instance.to_domain_tool(), plugin_name="builtin")

    async def get_available(self) -> Sequence[ToolSpec]:
        return list(self._specs.values())

    async def get_spec(self, name: str) -> ToolSpec | None:
        return self._specs.get(name)

    async def get_handler(self, name: str) -> Callable | None:
        return self._handlers.get(name)
    def register_spec(self, spec, handler):
        if spec.name in self._specs:
            raise ValueError(f"Duplicate tool: {spec.name}")
        self._specs[spec.name] = spec
        self._handlers[spec.name] = handler
