from backend.core.schemas.client_schema import MessageClientSchema
from .interfaces.recognizeABC import RecognizeABC
from logger import log


class ASRController:
    def __init__(self, recognizer: RecognizeABC):
        self.is_active = False
        self.recognizer: RecognizeABC = recognizer

        
    def handle_audio_chunk(self, audio_bytes: bytes):
        if not self.is_active:
            return
            

        text = self.recognizer.feed(audio_bytes)
        if text:
            return MessageClientSchema(
                type='complete',
                content=text
            )
        
        
    def handle_recognize_start(self, data: dict):
        """Начало распознавания"""
        self.is_active = True
        sample_rate = data.get("sample_rate", 16000)
        self.recognizer.start(sample_rate)
        return MessageClientSchema(
            type="start",
            content=''
        )
        
    def handle_recognize_end(self):
        if not self.is_active:
            return
            
        self.is_active = False
        final_text = self.recognizer.finish()
        log("Recognition completed", source=__name__)
        return MessageClientSchema(
            type='complete',
            content={
                "final_text": final_text,
                "is_final": True
            }
        )
        
        