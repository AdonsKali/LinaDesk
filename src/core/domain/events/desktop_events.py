from dataclasses import dataclass
from src.core.domain.events.base import DomainEvent


@dataclass(kw_only=True)
class DesktopActionRequested(DomainEvent):
    action: str
    value: str = ""
