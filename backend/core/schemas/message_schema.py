
from ast import List
from typing import Literal, Optional
from dataclasses import dataclass

@dataclass
class MessageHistory:
    role: Literal["system", "user", "assistant"]
    content: str | dict | list

    def __str__(self):
        return f"{self.role}: {self.content}"



