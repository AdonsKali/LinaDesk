from PySide6.QtWidgets import  QLabel, QWidget
from PySide6.QtCore import QTimer, Qt, QEvent, Signal
from PySide6.QtGui import QPixmap, QPainter, QImage
from paths import MEDIA


class Lina(QWidget):

    wake_up_signal = Signal()

    def __init__(self):
        super().__init__()
        self.body_animations = {
            "idle": [f"{MEDIA}/temp/LinaBase_peace.png"],
        }

        """model = AutoModelForCausalLM.from_pretrained(MERGED_MODEL_PATH)
        """
        self.emotions = {
            "neutral": {
                "face": f"{MEDIA}/temp/eyes.png",
                "blink": [f"{MEDIA}/temp/eyes.png", f"{MEDIA}/temp/eyes_closed.png"]
            },
        }

        self.current_body = "idle"
        self.current_emotion = "neutral"
        self.body_frame = 0
        self.blink_frame = 0
        self.is_blinking = False

        self.body_timer = QTimer()
        self.body_timer.timeout.connect(self.update_body_frame)
        self.body_timer.start(200)

        self.blink_timer = QTimer()
        self.blink_timer.timeout.connect(self.do_blink)
        self.blink_timer.start(4000)

        self.label = QLabel(self)
        self.label.setScaledContents(True)
        self.resize(160,200)
        self.set_body_animation("idle")
        self.set_emotion("neutral")
        self.update_sprite()


    def set_body_animation(self, name: str):
        if name in self.body_animations:
            self.current_body = name
            self.body_frame = 0


    def set_emotion(self, name: str):
        if name in self.emotions:
            self.current_emotion = name
            self.blink_frame = 0
            self.is_blinking = False
            self.update_sprite()


    def update_body_frame(self):
        frames = self.body_animations[self.current_body]
        self.body_frame = (self.body_frame + 1) % len(frames)
        self.update_sprite()


    def do_blink(self):
        if not self.is_blinking:
            self.is_blinking = True
            self.blink_sequence = self.emotions[self.current_emotion]["blink"]
            self.blink_frame = 0
            self.blink_anim_timer = QTimer()
            self.blink_anim_timer.timeout.connect(self.update_blink_frame)
            self.blink_anim_timer.start(100)


    def update_blink_frame(self):
        if self.blink_frame < len(self.blink_sequence):
            self.update_sprite()
            self.blink_frame += 1
        else:
            self.is_blinking = False
            self.blink_anim_timer.stop()
            self.update_sprite()


    def update_sprite(self):
        body_img = QImage(self.body_animations[self.current_body][self.body_frame])
        if self.is_blinking and self.blink_frame < len(self.blink_sequence):
            face_img = QImage(self.blink_sequence[self.blink_frame])
        else:
            face_img = QImage(self.emotions[self.current_emotion]["face"])

        combined = QImage(body_img.size(), QImage.Format_ARGB32)
        combined.fill(Qt.transparent)

        painter = QPainter(combined)
        painter.drawImage(0, 0, body_img)
        painter.drawImage(0, 0, face_img)
        painter.end()

        self.label.setPixmap(QPixmap.fromImage(combined))


    def resizeEvent(self, event):
        self.label.resize(self.size())

    
    def mouseDoubleClickEvent(self, event: QEvent):
        self.wake_up_signal.emit()

    


