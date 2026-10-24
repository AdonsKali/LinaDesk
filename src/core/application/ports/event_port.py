from typing import Type, Callable
from src.core.domain.events.base import DomainEvent


class EventBusPort:
    """Единый интерфейс для событий"""
    
    async def publish(self, event: DomainEvent) -> None:
        """Публикация события (только для Application слоя)"""
        raise NotImplementedError
    
    def subscribe(self, event_type: Type[DomainEvent], handler: Callable) -> None:
        """Подписка на события (только для Presentation слоя)"""
        raise NotImplementedError
    
    def unsubscribe(self, event_type: Type[DomainEvent], handler: Callable) -> None:
        """Отписка от событий"""
        raise NotImplementedError
    
    async def start(self) -> None:
        """Запуск шины"""
        raise NotImplementedError
    
    async def stop(self) -> None:
        """Остановка шины"""
        raise NotImplementedError

    async def drain(self) -> None:
        """Wait for delivery outside event handlers."""
        raise NotImplementedError
