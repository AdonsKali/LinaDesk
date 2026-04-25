from typing import Any, Literal, Dict, Optional, Union
from dataclasses import dataclass

@dataclass
class ToolSchemaOut:
    status: Literal["ok", "error"]
    msg: Optional[str] = None
    data: Optional[Dict] = None

@dataclass
class ToolSchema:
    name: str
    description: str
    parameters: Dict[Literal["type", "properties", "required"], Union[str, dict, list]]

@dataclass
class ToolCall:
    name: str
    arguments: Dict[str, Any]