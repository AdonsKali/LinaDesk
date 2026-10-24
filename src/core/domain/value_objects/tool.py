from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


class ToolPermission(str, Enum):
    """Permissions"""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    NETWORK = "network"


@dataclass
class Tool:
    """Tool registered in the system"""
    name: str
    description: str
    handler: Callable
    is_enabled: bool
    permissions: list[ToolPermission] = field(default_factory=list)
    parameters: dict[str, str] = field(default_factory=dict)


# =========================================================
# ToolSpec — описание инструмента для LLM
# =========================================================

@dataclass(frozen=True, slots=True)
class ToolParameter:
    name: str
    type: str                      # "string" | "integer" | "boolean" | "array"
    description: str
    required: bool = True
    enum: Optional[tuple[str, ...]] = None


@dataclass(frozen=True, slots=True)
class ToolSpec:
    """Описание инструмента для LLM. Без handler."""
    name: str
    description: str
    parameters: dict[str, ToolParameter]
    permissions: tuple[ToolPermission, ...]
    plugin_name: str
    background: bool = False
    timeout_seconds: float = 15
    trusted_builtin: bool = False

    @classmethod
    def from_tool(cls, tool: Tool, plugin_name: str) -> "ToolSpec":
        params = {
            name: ToolParameter(
                name=name,
                type="string",
                description=desc,
            )
            for name, desc in tool.parameters.items()
        }
        return cls(
            name=tool.name,
            description=tool.description,
            parameters=params,
            permissions=tuple(tool.permissions),
            plugin_name=plugin_name,
            trusted_builtin=plugin_name == "builtin",
        )

    def to_prompt_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    pname: {
                        "type": p.type,
                        "description": p.description,
                        **({"enum": list(p.enum)} if p.enum else {}),
                    }
                    for pname, p in self.parameters.items()
                },
                "required": [
                    pname for pname, p in self.parameters.items() if p.required
                ],
            },
        }


# =========================================================
# ToolCall — вызов инструмента
# =========================================================

@dataclass(frozen=True, slots=True)
class ToolCall:
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ToolResult:
    tool_name: str
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    requires_confirmation: bool = False
    missing_permissions: tuple[str, ...] = ()

    @classmethod
    def ok(cls, tool_name: str, output: str) -> "ToolResult":
        return cls(tool_name=tool_name, success=True, output=output)

    @classmethod
    def fail(cls, tool_name: str, error: str) -> "ToolResult":
        return cls(tool_name=tool_name, success=False, error=error)

    @classmethod
    def pending(cls, tool_name: str, missing: list[str]) -> "ToolResult":
        return cls(
            tool_name=tool_name,
            success=False,
            requires_confirmation=True,
            missing_permissions=tuple(missing),
        )

    def to_llm_content(self) -> str:
        if self.success:
            return f"Tool '{self.tool_name}' result: {self.output}"
        if self.requires_confirmation:
            return (
                f"Tool '{self.tool_name}' requires confirmation for: "
                f"{', '.join(self.missing_permissions)}"
            )
        return f"Tool '{self.tool_name}' failed: {self.error}"
