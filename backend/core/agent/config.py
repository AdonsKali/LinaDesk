
from dataclasses import dataclass
from typing import List

from backend.core.schemas.tool_schema import ToolSchema


@dataclass
class Config:
    name: str
    tools: List[ToolSchema]
    
    system_prompt: str = "You are a sweet assistant named Lina."
    max_steps: int = 8

