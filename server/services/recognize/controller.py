import logging
from ..init_services import recognize
logger = logging.getLogger(__name__)


class ASRController:
    def __init__(self, ws):
        self.ws = ws
        self.is_active = False
        
    async def handle_audio_chunk(self, audio_bytes: bytes):
        """Обработка аудио чанка"""
        if not self.is_active:
            return
            

        text = recognize.feed(audio_bytes)
        if text:
            await self.ws.send_json({
                "type": "recognition_result",
                "text": text
            })
        
        
    async def handle_recognize_start(self, data: dict):
        """Начало распознавания"""
        self.is_active = True
        sample_rate = data.get("sample_rate", 16000)
        recognize.start(sample_rate)
        
        await self.ws.send_json({
            "type": "recognition_started",
            "message": "Recognition started"
        })
        
    async def handle_recognize_end(self):
        if not self.is_active:
            return
            
        self.is_active = False
        final_text = recognize.finish()
        await self.ws.send_json({
            "type": "recognition_result",
            "text": final_text,
            "is_final": True
        })
        
        logger.info("Recognition completed")
        