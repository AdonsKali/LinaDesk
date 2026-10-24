from typing import Optional, Any


class DomainError(Exception):
    """
    Base exception for all domain-specific errors.
    
    All errors related to business rule violations
    must inherit from this class.
    """
    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None
    ):
        self.message = message
        self.code = code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


class InvalidStateError(DomainError):
    """The agent is in an invalid state to perform the operation."""
    pass


class ValidationError(DomainError):
    """Invalid input data"""
    pass


class NotFoundError(DomainError):
    """Entity not found"""
    pass


class PermissionError(DomainError):
    """Insufficient privileges to perform the operation."""
    pass


class EventBusError(Exception):
    pass


class CommandBusError(Exception):
    pass


class SubscriberError(Exception):
    """Error in the subscriber."""
    pass