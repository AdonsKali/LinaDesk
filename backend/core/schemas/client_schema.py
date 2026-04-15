from typing import Any, Dict, Literal, Optional, Union
from dataclasses import dataclass

@dataclass
class ClientToken:
    type: Literal["token"]
    content: str

@dataclass
class ClientComplete:
    type: Literal["complete"]
    
@dataclass
class ClientStart:
    type: Literal['start']

@dataclass
class ClientError:
    type: Literal["error"]
    message: str

@dataclass
class ClientAction:
    type: Literal['action']
    data: dict

@dataclass
class ClientToolCall:
    type: Literal['tool_call']
    data: dict


@dataclass
class MessageClientSchema:
    type: Literal['token', 'complete', 'start', 'error']
    content: Optional[Union[str, dict]] = None


