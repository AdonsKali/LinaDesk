import json
import pyaudio
from paths import VOSK_MODEL
from vosk import Model, KaldiRecognizer


class Recognize():
    def __init__(self):
        super().__init__()
        self.model = Model(f"{VOSK_MODEL}")
        self.p = pyaudio.PyAudio()

    def start(self, sample_rate=16000):
        self.recognizer = KaldiRecognizer(self.model, sample_rate)

    def feed(self, pcm_bytes: bytes):
        if self.recognizer.AcceptWaveform(pcm_bytes):
            res = json.loads(self.recognizer.Result())
            return res.get("text")

    def finish(self):
        res = json.loads(self.recognizer.FinalResult())
        return res.get("text")