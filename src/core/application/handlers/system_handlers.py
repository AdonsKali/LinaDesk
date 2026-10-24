from src.core.application.ports.command_bus import CommandHandlerPort
from src.core.application.ports.event_port import EventBusPort as EventBus
from src.core.application.commands.system_commands import StartSystemCommand, StopSystemCommand
from src.core.domain.events.system_events import SystemStartRequested, SystemStopRequested, SystemError, SystemStopped
from src.core.application.ports.repositories import SettingsRepository
from src.core.utils.logger import logger
logger = logger.get(__name__)


class StartSystemHandler(CommandHandlerPort):
    """
    Обработчик команды запуска системы..
    """
    
    def __init__(
        self,
        settings_repo: SettingsRepository,
        event_bus: EventBus
    ):
        self._settings_repo = settings_repo
        self._event_bus = event_bus
    
    async def handle(self, command: StartSystemCommand) -> None:
        """Обработка команды запуска"""
        logger.info("StartSystemHandler: Processing start command...")
        
        # 1. Проверяем настройки
        settings = await self._settings_repo.get()
        if not settings:
            await self._event_bus.publish(
                SystemError(
                    error="Settings not found. Please configure the system first.",
                    component="launcher"
                )
            )
            return
        
        errors = self._validate_settings(settings)
        if errors:
            await self._event_bus.publish(
                SystemError(
                    error="; ".join(errors),
                    component="launcher"
                )
            )
            return
        
        await self._event_bus.publish(
            SystemStartRequested(
                settings=settings.to_dict()
            )
        )
        
        logger.info("StartSystemHandler: SystemStartRequested published")
    
    def _validate_settings(self, settings) -> list:
        errors = []
        if not settings.username or len(settings.username.strip()) < 1:
            errors.append("Username is required")
        if settings.language not in ["en", "ru", "zh"]:
            errors.append("Invalid language selected")
        return errors
    

class StopSystemHandler(CommandHandlerPort):
    """
    Обработчик команды остановки системы.
    """
    
    def __init__(self, event_bus: EventBus):
        self._event_bus = event_bus
    
    async def handle(self, command: StopSystemCommand) -> None:
        """Обработка команды остановки"""
        logger.info(f"StopSystemHandler: Processing stop command (reason: {command.reason})...")
        
        await self._event_bus.publish(
            SystemStopRequested(reason=command.reason)
        )
        
        logger.info("StopSystemHandler: SystemStopRequested published")
