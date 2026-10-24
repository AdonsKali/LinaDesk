import asyncio
import logging
from typing import Dict, List, Callable, Optional, Type, Any
from src.core.domain.events.base import DomainEvent
from src.core.application.ports import EventBusPort


class EventBus(EventBusPort):
    """
    Простая реализация Event Bus.
    Один класс - один интерфейс.
    """
    
    def __init__(self):
        self._handlers: Dict[Type[DomainEvent], List[Callable]] = {}
        self._queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None
        self._is_closing = False
    
    async def publish(self, event: DomainEvent) -> None:
        """Публикация события"""
        if self._is_closing or not self._running:
            return
        
        await self._queue.put(event)
    
    def subscribe(self, event_type: Type[DomainEvent], handler: Callable) -> None:
        """Подписка на событие"""
        if self._is_closing:
            return
        
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        
        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)
    
    def unsubscribe(self, event_type: Type[DomainEvent], handler: Callable) -> None:
        """Отписка от события"""
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
                if not self._handlers[event_type]:
                    del self._handlers[event_type]
            except ValueError:
                pass
    
    async def start(self) -> None:
        """Запуск шины"""
        if self._running:
            return
        
        self._running = True
        self._is_closing = False
        self._worker_task = asyncio.create_task(self._worker())
    
    async def stop(self) -> None:
        """Остановка шины"""
        self._is_closing = True
        self._running = False
        
        if self._worker_task and not self._worker_task.done():
            self._worker_task.cancel()
            try:
                await asyncio.wait_for(self._worker_task, timeout=2.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            self._worker_task = None
        
        # Очищаем очередь
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except asyncio.QueueEmpty:
                break
        
        self._handlers.clear()
    
    async def _worker(self) -> None:
        """Воркер для обработки событий"""
        while self._running and not self._is_closing:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=0.5)
                try:
                    await self._process_event(event)
                finally:
                    self._queue.task_done()
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error processing event: {e}")
    
    async def _process_event(self, event: DomainEvent) -> None:
        """Обработка события"""
        event_type = type(event)
        handlers = list(self._handlers.get(event_type, []))
        
        # Обрабатываем дочерние классы
        for handler_type, handler_list in self._handlers.items():
            if issubclass(event_type, handler_type) and handler_type != event_type:
                handlers.extend(handler_list)
        
        handlers = list(dict.fromkeys(handlers))
        
        if not handlers:
            return
        
        # Выполняем обработчики параллельно
        tasks = []
        for handler in handlers:
            if asyncio.iscoroutinefunction(handler):
                tasks.append(handler(event))
            else:
                async def invoke(callback=handler):
                    callback(event)
                tasks.append(invoke())
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    logging.getLogger(__name__).error("Event handler failed: %s", result, exc_info=result)
    
    async def drain(self):
        """Wait for queued notifications; call only outside event handlers."""
        await self._queue.join()

    def get_stats(self) -> Dict[str, Any]:
        """Получение статистики"""
        return {
            "handlers_count": sum(len(h) for h in self._handlers.values()),
            "queue_size": self._queue.qsize(),
            "is_running": self._running
        }
