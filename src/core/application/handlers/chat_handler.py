from src.core.application.commands.chat_commands import SendMessageCommand
from src.core.application.orchestration.chat_orchestration import ChatOrchestration
from src.core.application.ports.command_bus import CommandHandlerPort
from src.core.utils.logger import logger
logger = logger.get(__name__)


class SendMessageHandler(CommandHandlerPort[SendMessageCommand]):
    """Обработчик SendMessageCommand — тонкий, всё в orchestration."""

    def __init__(self, orchestration: ChatOrchestration):
        self._orchestration = orchestration

    async def handle(self, command: SendMessageCommand) -> None:
        logger.info(
            f"[ChatHandler] handle id(self)={id(self)} "
            f"text={command.text[:30]!r}"
            f"data_files={command.data_files}"
        )
        await self._orchestration.process_user_message(command)