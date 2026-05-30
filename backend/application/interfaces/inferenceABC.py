from abc import ABC, abstractmethod
from typing import Dict, List
from typing import AsyncGenerator


class InferenceABC(ABC):
    """Abstract class for LLM inference"""

    @abstractmethod
    def generate(self, prompt: List[Dict]) -> str:
       ...

    @abstractmethod
    async def stream(self, prompt: List[Dict], tools: List[dict], generation_params: dict
                     ) -> AsyncGenerator:
        ...

