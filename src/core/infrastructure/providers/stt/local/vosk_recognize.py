import asyncio
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


class VoskRecognizer:
    def __init__(self, model_path):
        self.model_path = Path(model_path)
        self._model = None
        self._executor = None
        self._lock = asyncio.Lock()
        self._closed = False

    async def transcribe(self, pcm: bytes, sample_rate: int) -> str:
        async with self._lock:
            if self._closed:
                raise RuntimeError("Speech recognizer is closed")
            if sample_rate <= 0 or len(pcm) % 2:
                raise ValueError("Expected mono signed 16-bit PCM and a positive sample rate")
            if not pcm:
                return ""
            if self._executor is None:
                self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="lina-vosk")
            cancelled = threading.Event()
            def recognize():
                if not self.model_path.is_dir():
                    raise ValueError(f"Не найдена модель Vosk: {self.model_path}")
                from vosk import Model, KaldiRecognizer
                if self._model is None:
                    self._model = Model(str(self.model_path))
                recognizer = KaldiRecognizer(self._model, sample_rate)
                parts = []
                for offset in range(0, len(pcm), 8000):
                    if cancelled.is_set():
                        return ""
                    if recognizer.AcceptWaveform(pcm[offset:offset + 8000]):
                        parts.append(json.loads(recognizer.Result()).get("text", ""))
                parts.append(json.loads(recognizer.FinalResult()).get("text", ""))
                return " ".join(part.strip() for part in parts if part.strip())
            future = asyncio.get_running_loop().run_in_executor(self._executor, recognize)
            try:
                return await asyncio.shield(future)
            except asyncio.CancelledError:
                cancelled.set()
                while not future.done():
                    try:
                        await asyncio.shield(future)
                    except asyncio.CancelledError:
                        continue
                    except Exception:
                        break
                if not future.cancelled():
                    future.exception()
                raise

    async def close(self):
        async with self._lock:
            self._closed = True
            if self._executor:
                def release():
                    self._model = None
                future = asyncio.get_running_loop().run_in_executor(self._executor, release)
                await asyncio.shield(future)
                self._executor.shutdown(wait=True)
                self._executor = None
