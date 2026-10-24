from src.core.domain.entities.lina import Lina
from src.core.domain.entities.user import User
from src.core.domain.entities.message import Message, MessageType, MessageRole
from src.core.domain.entities.session import Session

# Value Objects
from src.core.domain.value_objects.emotion import Emotion, EmotionType, Valence
from src.core.domain.value_objects.mood import Mood, MoodType
from src.core.domain.value_objects.personality_trait import PersonalityTrait, TraitType
from src.core.domain.value_objects.memory_fragment import MemoryFragment
from src.core.domain.value_objects.autonomy import Thought, AutonomyAction

# Domain Events
from src.core.domain.events.base import DomainEvent
from src.core.domain.events.message_events import (
    MessageReceived, MessageProcessed, ResponseGenerated
)
from src.core.domain.events.emotion_events import (
    EmotionChanged, MoodChanged, EmotionIntensified, EmotionWeakened
)
from src.core.domain.events.thought_events import ThoughtGenerated
from src.core.domain.events.tool_events import ToolExecuted
from src.core.domain.events.memory_events import MemoryStored, MemoryRecalled, MemoryForgotten
from src.core.domain.events.session_events import SessionStarted, SessionEnded
from src.core.domain.events.autonomy_events import (
    AutonomousAction
)
from src.core.domain.domain_error import (
    DomainError, InvalidStateError, ValidationError,
    NotFoundError, PermissionError
)



__all__ = [
    # Entities
    "Lina", "User", "Message", "Session",
    "MessageType", "MessageRole",
    
    # Value Objects
    "Emotion", "EmotionType", "Valence",
    "Mood", "MoodType",
    "PersonalityTrait", "TraitType",
    "MemoryFragment",
    "Thought", "AutonomyAction",
    
    # Domain Events
    "DomainEvent",
    "MessageReceived", "MessageProcessed", "ResponseGenerated",
    "EmotionChanged", "MoodChanged", "EmotionIntensified", "EmotionWeakened",
    "ThoughtGenerated",
    "ToolExecuted",
    "MemoryStored", "MemoryRecalled", "MemoryForgotten",
    "SessionStarted", "SessionEnded",
    "AutonomousAction",
    
    # Exceptions
    "DomainError", "InvalidStateError", "ValidationError",
    "NotFoundError", "PermissionError",
]