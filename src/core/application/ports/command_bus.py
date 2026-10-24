from abc import ABC, abstractmethod
from typing import Any, TypeVar, Generic

# Тип для команды
T = TypeVar('T', bound='Command')


class Command(ABC):
    """Базовый класс для команд"""
    pass


class CommandHandlerPort(ABC, Generic[T]):
    """
    Базовый класс для обработчиков команд с Generic.
    
    Пример:
        class StartSystemHandler(CommandHandler[StartSystemCommand]):
            async def handle(self, command: StartSystemCommand) -> None:
                ...
    """
    
    @abstractmethod
    async def handle(self, command: T) -> Any:
        """Обработка команды"""
        pass


class CommandBusPort(ABC):
    """Шина команд"""
    
    @abstractmethod
    async def send(self, command: Command) -> Any:
        """Отправка команды"""
        pass
    
    @abstractmethod
    def register(self, command_type: type[Command], handler: CommandHandlerPort) -> None:
        """Регистрация обработчика"""
        pass