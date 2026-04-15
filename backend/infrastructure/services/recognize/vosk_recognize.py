import json
import pyaudio
from backend.application.interfaces.recognizeABC import RecognizeABC
from vosk import Model, KaldiRecognizer


class VoskRecognizer(RecognizeABC):
    def __init__(self, model_path: str):
        super().__init__()
        self.model = Model(model_path)
        self.p = pyaudio.PyAudio()

    def start(self, sample_rate=16000):
        self.recognizer = KaldiRecognizer(self.model, sample_rate)
        return True

    def feed(self, pcm_bytes: bytes):
        if self.recognizer.AcceptWaveform(pcm_bytes):
            res = json.loads(self.recognizer.Result())
            return res.get("text")

    def finish(self):
        res = json.loads(self.recognizer.FinalResult())
        return res.get("text")