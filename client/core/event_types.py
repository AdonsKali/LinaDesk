from enum import Enum, auto

class EventType(Enum):
    """Типы событий в системе"""
    USER_TEXT_SUBMITTED = auto()
    USER_VOICE_STARTED = auto()
    USER_VOICE_STOPPED = auto()
    USER_CHIBI_CLICKED = auto()
    USER_CHIBI_DRAGGED = auto()
    

    AI_RESPONSE_STARTED = auto()
    AI_TOKEN_RECEIVED = auto()
    AI_RESPONSE_COMPLETED = auto()
    AI_ERROR_OCCURRED = auto()
    AI_TOOL_CALL_STARTED = auto()
    AI_TOOL_CALL_COMPLETED = auto()
    
    CHIBI_STATE_CHANGED = auto()
    CHIBI_ANIMATION_CHANGED = auto()
    CHIBI_POSITION_CHANGED = auto()
    
    BUBBLE_VISIBILITY_CHANGED = auto()
    BUBBLE_TEXT_CHANGED = auto()
    CHAT_VISIBILITY_CHANGED = auto()
    CHAT_PROCESSING_CHANGED = auto()
    BUBBLE_POSITION_UPDATED = auto()
    CHAT_POSITION_UPDATED = auto()

