import json
import re
from abc import ABC, abstractmethod
from typing import Any, List, Optional, Dict, AsyncGenerator
from dataclasses import dataclass, field


_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)
_THOUGHT_RE = re.compile(r"<\|channel>.*?<channel\|>", re.DOTALL)


@dataclass
class ChatMessage:
    role: str
    content: "str | list[dict]"
    name: Optional[str] = None


@dataclass
class ChatResponse:
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    usage: Dict[str, int] = field(default_factory=dict)
    model: str = "unknown"
    finish_reason: str = "stop"


class LLMPort(ABC):

    @abstractmethod
    async def generate(
        self,
        messages: List[ChatMessage] | str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> ChatResponse | str: ...

    @abstractmethod
    async def stream_generate(
        self,
        messages: List[ChatMessage] | str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        tools: Optional[List[Dict[str, Any]]] = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]: ...

    @abstractmethod
    async def embed(self, text: str) -> List[float]: ...

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]: ...

    @abstractmethod
    def get_embedding_dim(self) -> int: ...

    @abstractmethod
    async def initialize(self) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...

    @abstractmethod
    def is_initialized(self) -> bool: ...

    # ─── Не-абстрактный метод с реализацией по умолчанию ───
    async def infer_json(
        self,
        messages: List[ChatMessage] | str,
        **kwargs,
    ) -> Any:
        """
        Обёртка над generate: возвращает распарсенный JSON.
        Устойчива к:
        - markdown-обёртке ```json ... ```
        - Gemma 4 thinking-блоку <|channel>thought...<channel|>
        - мусору вокруг JSON
        """
        response = await self.generate(messages, **kwargs)
        text = response.content if isinstance(response, ChatResponse) else response
        text = text.strip()

        # Убираем thinking-блок Gemma 4
        text = _THOUGHT_RE.sub("", text).strip()

        # Убираем markdown-обёртку
        if text.startswith("```"):
            # убрать первые ```
            text = text[3:]
            if text.lower().startswith("json"):
                text = text[4:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        # Пробуем распарсить как есть
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Arrays and objects, including prose and code fences around JSON.
        decoder = json.JSONDecoder()
        for index, char in enumerate(text):
            if char not in "[{":
                continue
            try:
                result, _ = decoder.raw_decode(text[index:])
                return result
            except json.JSONDecodeError:
                pass

        raise ValueError(
            f"Could not parse JSON from LLM response: {text[:300]!r}"
        )
