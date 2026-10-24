from dataclasses import dataclass
from typing import Optional
from uuid import UUID
from src.core.domain.events.base import DomainEvent
from src.core.domain.entities.message import Message


@dataclass(kw_only=True)
class MessageReceived(DomainEvent):
    """
    Event: message received from a user.
    
    Occurs when a user has sent a message to an agent.
    """
    session_id: str | None = None
    message: Message | None = None
    user_id: str | None = None

    def __post_init__(self):
        self.aggregate_id = self.message.id #type: ignore


@dataclass(kw_only=True)
class MessageProcessed(DomainEvent):
    """
    Event: message processed by the agent.
    
    Occurs when the agent has finished processing a user message.
    """
    original_message_id: UUID
    response_message: Message
    session_id: UUID
    processing_time_ms: Optional[float] = None

    def __post_init__(self):
        self.aggregate_id = str(self.response_message.id)


@dataclass(kw_only=True)
class ResponseGenerated(DomainEvent):
    """
    Event: message sent by an agent.
    
    Occurs when an agent has sent a message to a user.
    """
    message: Message
    session_id: str
    agent_id: str

    def __post_init__(self):
        self.aggregate_id = str(self.message.id)



@dataclass(kw_only=True)
class StreamChunk(DomainEvent):
    """
    Event: a fragment of the generated response (token/chunk).

    Used for the incremental transmission of data to the presentation layer.
    """
    session_id: str
    chunk: str
    partial_message_id: str | None = None

    def __post_init__(self):
        if isinstance(self.session_id, UUID):
            self.aggregate_id = str(self.session_id)