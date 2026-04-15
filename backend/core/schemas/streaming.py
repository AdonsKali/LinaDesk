from dataclasses import dataclass
from typing import Literal, Union, TypedDict
from backend.core.schemas.tool_schema import ToolCall

@dataclass
class TokenChunk:
    type: Literal["token"]
    content: str
    
@dataclass
class ToolCallChunk:
    type: Literal["tool_call"]
    tool: ToolCall

@dataclass
class StreamComplete:
    type: Literal["complete"]

@dataclass
class StreamError:
    type: Literal["error"]
    message: str