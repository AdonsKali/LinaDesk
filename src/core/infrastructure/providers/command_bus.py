from typing import Dict, Type, Any
from src.core.application.ports.command_bus import Command, CommandHandlerPort, CommandBusPort
from src.core.utils.logger import logger
logger = logger.get(__name__)

class CommandBus(CommandBusPort):
    """Простая реализация Command Bus"""
    
    def __init__(self):
        self._handlers: Dict[Type[Command], CommandHandlerPort] = {}
    
    def register(self, command_type: Type[Command], handler: CommandHandlerPort) -> None:
        """Регистрация обработчика"""
        self._handlers[command_type] = handler
    
    async def send(self, command: Command) -> Any:
        """Отправка команды"""
        handler = self._handlers.get(type(command))
        if not handler:
            logger.error(f"No handler registered for command: {type(command)}")
            raise ValueError(f"No handler registered for command: {type(command)}")
        handler_name = type(handler).__name__
        logger.debug(f"Sending command: {type(command).__name__} with handler: {handler_name}")
        return await handler.handle(command)