from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class Thought:
    """
    Мысль Лины — что она хочет сделать прямо сейчас.

    Генерируется LLM на основе:
    - текущей эмоции / mood
    - характера
    - памяти
    - последнего сообщения
    """
    id: UUID
    content: str                       # «Хочу рассказать Андрею про...»
    confidence: float                  # 0.0 - 1.0
    created_at: datetime
    triggered_by: Optional[str] = None

    @classmethod
    def create(
        cls,
        content: str,
        confidence: float = 0.5,
        triggered_by: Optional[str] = None,
    ) -> "Thought":
        return cls(
            id=uuid4(),
            content=content,
            confidence=max(0.0, min(1.0, confidence)),
            created_at=datetime.now(),
            triggered_by=triggered_by,
        )


@dataclass(frozen=True, slots=True)
class AutonomyAction:
    """
    Действие, которое Лина решила сделать после мысли.

    Типы:
    - "message" — написать пользователю
    - "tool" — вызвать инструмент
    - "none" — просто подумать (записать в память)
    """
    type: str                          # "message" | "tool" | "none"
    content: Optional[str] = None      # текст сообщения (для message)
    tool_name: Optional[str] = None    # имя инструмента (для tool)
    tool_arguments: dict[str, Any] = field(default_factory=dict)