from abc import ABC, abstractmethod
from typing import List

from backend.core.agent.config import Config
from backend.core.schemas.tool_schema import ToolSchema
from ..schemas.message_schema import MessageHistory
from .state import State


class Agent():
    def __init__(self):
        super().__init__() 
        self.state = State.IDLE
        self.config: Config


        self.name: str
        self.tools: List[ToolSchema]
        self.system_prompt: str
        self.max_steps: int
        self.temperature: float

        self.history: List[MessageHistory] = []
        

    def reset(self):
        self.history.clear()
        self.state = State.IDLE


    def add_message(self, message: MessageHistory):
        self.history.append(message)


    def remove_message(self, message: MessageHistory):
        self.history.remove(message)


    def get_history(self) -> List[MessageHistory]:
        return self.history


    def get_last(self) -> MessageHistory:
        return self.history[-1]
    

    def get_state(self):
        return self.state
    

    def set_cfg(self, cfg: Config):
        self.config = cfg


