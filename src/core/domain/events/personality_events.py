from dataclasses import dataclass
from src.core.domain.events.base import DomainEvent


@dataclass
class PersonalityTraitChanged(DomainEvent):
    """
    Событие: Личность изменилась
    """
    name: str
    value: float
    