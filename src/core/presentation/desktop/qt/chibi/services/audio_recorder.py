"""Bounded mono PCM capture; native input stream belongs to the worker."""
import sounddevice as sd
from PySide6.QtCore import QThread, Signal


class AudioRecorder(QThread):
    recording_ready = Signal(bytes, int)
    error_occurred = Signal(str)

    def __init__(self, sample_rate=16000, device=None):
        super().__init__()
        self.sample_rate = sample_rate
        self.device = device

    def run(self):
        chunks = []
        frames = 0
        try:
            with sd.RawInputStream(samplerate=self.sample_rate, channels=1,
                                   dtype="int16", blocksize=1600, device=self.device) as stream:
                while not self.isInterruptionRequested() and frames < self.sample_rate * 60:
                    data, _ = stream.read(1600)
                    chunks.append(bytes(data))
                    frames += 1600
            if chunks:
                self.recording_ready.emit(b"".join(chunks), self.sample_rate)
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    def stop(self):
        self.requestInterruption()

    def cleanup(self):
        self.stop()
        self.wait()
