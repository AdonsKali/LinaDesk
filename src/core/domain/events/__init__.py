"""
Domain Events Module
"""

from src.core.domain.events.autonomy_events import (
    AutonomyChanged,
    AutonomousAction,
)
from src.core.domain.events.base import DomainEvent
from src.core.domain.events.emotion_events import (
    EmotionChanged,
    EmotionIntensified,
    EmotionWeakened,
    MoodChanged,
)
from src.core.domain.events.lina_events import (
    LinaStatusChanged,
    NameChanged,
)
from src.core.domain.events.memory_events import (
    MemoryForgotten,
    MemoryRecalled,
    MemoryStored,
)
from src.core.domain.events.message_events import (
    MessageProcessed,
    MessageReceived,
    ResponseGenerated,
    StreamChunk,
)
from src.core.domain.events.personality_events import PersonalityTraitChanged
from src.core.domain.events.plugin_events import (
    PluginDisabled,
    PluginEnabled,
    PluginToggled,
    PluginListReceived,
    PluginListRequested
)
from src.core.domain.events.session_events import (
    SessionEnded,
    SessionStarted,
)
from src.core.domain.events.settings_events import (
    SettingsChanged,
    SettingsLoaded,
    SettingsReset,

)
from src.core.domain.events.system_events import (
    SystemError,
    SystemRestartRequested,
    SystemStarted,
    SystemStartRequested,
    SystemStopped,
    SystemStopRequested,
)
from src.core.domain.events.thought_events import (
    ThoughtGenerated,
)
from src.core.domain.events.tool_events import (
    ToolExecuted,
)

__all__ = [
    # Base
    "DomainEvent",
    
    # Autonomy Events
    "AutonomyChanged",
    "AutonomousAction",
    
    # Emotion Events
    "EmotionChanged",
    "EmotionIntensified",
    "EmotionWeakened",
    "MoodChanged",
    
    # Lina Events
    "LinaStatusChanged",
    "NameChanged",
    
    # Memory Events
    "MemoryForgotten",
    "MemoryRecalled",
    "MemoryStored",
    
    # Message Events
    "MessageProcessed",
    "MessageReceived",
    "ResponseGenerated",
    "StreamChunk",
    
    # Personality Events
    "PersonalityTraitChanged",
    
    # Plugin Events
    "PluginDisabled",
    "PluginEnabled",
    "PluginListReceived",
    "PluginListRequested",
    "PluginToggled",
    
    # Session Events
    "SessionEnded",
    "SessionStarted",
    
    # Settings Events
    "SettingsChanged",
    "SettingsLoaded",
    "SettingsReset",
    
    # System Events
    "SystemError",
    "SystemRestartRequested",
    "SystemStarted",
    "SystemStartRequested",
    "SystemStopped",
    "SystemStopRequested",
    
    # Thought Events
    "ThoughtGenerated",
    
    # Tool Events
    "ToolExecuted",
]