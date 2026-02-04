from PySide6.QtCore import QObject, Signal, QTimer
import struct
from paths import MEDIA
from PySide6.QtGui import QPixmap, QImage


class Animation:
    def __init__(self, obj: QObject):
        self.animation_delay = QTimer()
        self.frames: list = [QPixmap]
        self.index: int = 0
        self.obj: QObject = obj


    def load_animation(self, ANIM_file: str):
        frames: list = []

        with open(f"{MEDIA}/animations/{ANIM_file}", 'rb') as f:
            if f.read(4) != b'ANIM':
                raise ValueError("Invalid animation file")

            frame_count: tuple = struct.unpack('<H', f.read(2))[0]

            for _ in range(frame_count):
                size: tuple = struct.unpack('<I', f.read(4))[0]
                img_data = f.read(size)
                image: QImage = QImage()
                image.loadFromData(img_data)
                pixmap: QPixmap = QPixmap.fromImage(image)
                frames.append(pixmap)

        self.frames = frames


    def start_animation(self, frequency: int, loop: bool = True):
        if loop:
            self.animation_delay: QTimer = QTimer()
            self.animation_delay.timeout.connect(self._update_animation)
            self.animation_delay.start(frequency)
        else:
            self._update_animation()

    
    def stop_animation(self):
        self.animation_delay.stop()


    def _update_animation(self):
        if self.index <= len(self.frames):
            self.obj.setPixmap(self.frames[self.index])
            self.index = (self.index + 1) % len(self.frames)
        else:
            self.index = 0