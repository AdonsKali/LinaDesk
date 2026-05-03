import pyaudio
from PySide6.QtCore import QThread, Signal


class AudioRecorder(QThread):
    """Поток записи аудио"""
    
    audio_chunk = Signal(bytes)
    error_occurred = Signal(str)
    finished = Signal()
    
    def __init__(self, sample_rate: int = 16000):
        super().__init__()
        self.sample_rate = sample_rate
        self._running = False
        self._pyaudio = None
        self._stream = None
    
    def run(self):
        """Основной цикл записи"""
        self._running = True
        
        try:
            self._pyaudio = pyaudio.PyAudio()
            self._stream = self._pyaudio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=4000
            )
            
            while self._running:
                try:
                    data = self._stream.read(4000, exception_on_overflow=False)
                    self.audio_chunk.emit(data)
                except Exception as e:
                    if self._running:
                        self.error_occurred.emit(str(e))
                    break
                    
        except Exception as e:
            self.error_occurred.emit(str(e))
        finally:
            self._cleanup()
            self.finished.emit()
    
    def stop(self):
        """Остановка записи"""
        self._running = False
        if self.wait(3000): 
            print("AudioRecorder thread stopped successfully")
        else:
            print("AudioRecorder thread did not stop in time, terminating")
    
    def _cleanup(self):
        """Очистка ресурсов"""
        try:
            if self._stream:
                self._stream.stop_stream()
                self._stream.close()
                self._stream = None
        except:
            pass
        
        try:
            if self._pyaudio:
                self._pyaudio.terminate()
                self._pyaudio = None
        except:
            pass
    
    def __del__(self):
        if self.isRunning():
            print("Warning: AudioRecorder destroyed while still running, attempting cleanup")
            self.stop()