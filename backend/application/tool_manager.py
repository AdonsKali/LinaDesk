from typing import Callable, List, Any
from functools import lru_cache

from backend.core.schemas.tool_schema import ToolSchemaOut

class Tool:
    def __init__(self, name: str, description: str, parameters: dict, func: Callable[[], ToolSchemaOut]):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.func = func

    def to_llm(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
    
    def execute(self, **kwargs) -> ToolSchemaOut:
        """Execute the tool with given arguments"""
        return self.func(**kwargs)



class ToolManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools = {}
        return cls._instance
    
    def register(self, tool: Tool) -> None:
        """Register a tool"""
        self._tools[tool.name] = tool
    
    def get(self, name: str) -> Tool:
        """Get tool by name"""
        return self._tools.get(name)

    def get_many(self, names: list[str]) -> list[Tool]:
        """Get multiple tools by names"""
        return [self._tools[n] for n in names if n in self._tools]
    
    def get_all(self) -> list[Tool]:
        """Get all registered tools"""
        return list(self._tools.values())
    
    def get_llm_descriptions(self) -> list[dict]:
        """Get tool descriptions formatted for LLM"""
        return [tool.to_llm() for tool in self._tools.values()]
    
    def get_llm_descriptions_by_names(self, names: list[str]) -> list[dict]:
        """Get LLM descriptions for specific tools by names"""
        return [self._tools[n].to_llm() for n in names if n in self._tools]
    
    def execute(self, name: str, **kwargs) -> ToolSchemaOut:
        """Execute a tool by name"""
        tool = self.get(name)
        if not tool:
            raise ValueError(f"Tool '{name}' not found")
        return tool.execute(**kwargs)
    
    @property
    def names(self) -> List[str]:
        return list(self._tools.keys())