from enum import Enum, auto


class State(Enum):
    
    PROCESSING = auto()
    IDLE = auto()
    EXECUTING = auto()
    RESPONDING = auto()
