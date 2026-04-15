from abc import ABC, abstractmethod
from typing import List, Union
from typing import AsyncGenerator
from backend.core.schemas import MessageHistory
from backend.core.schemas.streaming import (
    StreamComplete,
    StreamError,
    TokenChunk,
    ToolCallChunk
)


class InferenceABC(ABC):
    """Abstract class for LLM inference"""

    @abstractmethod
    def generate(self, prompt: List[MessageHistory]) -> str:
       ...

    @abstractmethod
    async def stream(self, prompt: List[MessageHistory]
                     ) -> AsyncGenerator:
        ...
