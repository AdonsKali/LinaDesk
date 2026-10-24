from src.core.application.commands.speech_commands import RecognizeSpeechCommand
from src.core.application.orchestration.runtime_gate import RuntimeGate
from src.core.application.ports.command_bus import CommandHandlerPort
from src.core.application.ports.event_port import EventBusPort
from src.core.application.ports.speech_port import SpeechRecognizerPort
from src.core.domain.events.speech_events import SpeechRecognized, SpeechRecognitionFailed


class RecognizeSpeechHandler(CommandHandlerPort[RecognizeSpeechCommand]):
    def __init__(self, recognizer: SpeechRecognizerPort, event_bus: EventBusPort, gate: RuntimeGate):
        self._recognizer, self._bus, self._gate = recognizer, event_bus, gate

    async def handle(self, command: RecognizeSpeechCommand) -> None:
        self._gate.touch()
        try:
            async with self._gate.lock:
                if self._gate.stopping:
                    raise RuntimeError("Система останавливается.")
                if not isinstance(command.pcm, bytes) or not command.pcm or len(command.pcm) % 2:
                    raise ValueError("Ожидается непустая запись mono PCM signed 16-bit.")
                if type(command.sample_rate) is not int or not 8000 <= command.sample_rate <= 48000:
                    raise ValueError("Частота записи должна быть от 8000 до 48000 Гц.")
                if len(command.pcm) > command.sample_rate * 2 * 60:
                    raise ValueError("Запись должна быть не длиннее 60 секунд.")
                text = (await self._recognizer.transcribe(command.pcm, command.sample_rate)).strip()
                if not text:
                    raise ValueError("Речь не распознана. Попробуйте ещё раз.")
                await self._bus.publish(SpeechRecognized(request_id=command.request_id, text=text))
        except Exception as exc:
            await self._bus.publish(SpeechRecognitionFailed(request_id=command.request_id, error=str(exc)))
        finally:
            self._gate.touch()
