from abc import ABC, abstractmethod
from typing import List
from typing import AsyncGenerator
from backend.core.schemas import MessageHistory


class InferenceABC(ABC):
    """Abstract class for LLM inference"""

    @abstractmethod
    def generate(self, prompt: List[MessageHistory]) -> str:
       ...

    @abstractmethod
    async def stream(self, prompt: List[MessageHistory]
                     ) -> AsyncGenerator:
        ...
