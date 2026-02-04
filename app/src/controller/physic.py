from PySide6.QtCore import QTimer, Qt, QObject
from time import time
import screeninfo
import pymunk


class Physic():
    def __init__(self, obj: QObject):
        super().__init__()
        self.obj = obj
        self.physics_flag = False
        self.space = pymunk.Space()
        self.space.gravity = (0, 1000)

        mass = 5
        width, height = self.obj.width(), self.obj.height()
        moment = pymunk.moment_for_box(mass, (width, height))
        self.body = pymunk.Body(mass, moment)
        self.body.position = (400, 100)
        self.shape = pymunk.Poly.create_box(self.body, (width, height))
        self.shape.elasticity = 0.3
        self.shape.friction = 0.8
        self.space.add(self.body, self.shape)

        # Земля
        x, y = screeninfo.get_monitors()[0].width, screeninfo.get_monitors()[0].height

        # Линия от левого до правого края
        ground = pymunk.Segment(self.space.static_body, (0, y), (x, y), 0.0)
        ground.elasticity = 0.55
        ground.friction = 1.0
        self.space.add(ground)

        # Флаг “перетаскивания”
        self.dragging = False
        self.drag_offset = (0, 0)

        # Таймер физики
        self.physics_timer = QTimer()
        self.physics_timer.timeout.connect(self.update_physics)
        self.physics_timer.start(16)

    def update_physics(self):
        if self.dragging:  
            return
        dt = 1 / 60.0
        self.space.step(dt)
        x, y = self.body.position
        self.obj.move(int(x), int(y))

    @classmethod
    def mouse_press_event(self, event, func):
        def wrapper(*args, **kwargs):
            self.dragging = True
            self.drag_offset = event.pos()
            self.drag_positions = []  
            func()
        return wrapper


    def mouse_move_event(self, event):
        if self.dragging:
            new_pos = self.obj.pos() + (event.pos() - self.drag_offset)
            self.move(new_pos)
            now = time()
            self.drag_positions.append((now, new_pos.x(), new_pos.y()))
            cutoff = now - 0.1
            self.drag_positions = [
                (t, x, y) for (t, x, y) in self.drag_positions if t > cutoff
            ]


    def mouse_release_event(self):
        self.dragging = False
        x, y = float(self.obj.pos().x()), float(self.obj.pos().y())
        self.body.position = (x, y)

        # === вычисляем скорость броска ===
        vx = vy = 0.0
        if len(self.drag_positions) >= 2:
            (t1, x1, y1), (t2, x2, y2) = self.drag_positions[0], self.drag_positions[-1]
            dt = t2 - t1
            if dt > 0:
                vx = (x2 - x1) / dt
                vy = (y2 - y1) / dt

        self.drag_positions.clear()

        # === применяем импульс ===
        damping = 0.3  # ← уменьшает скорость примерно в 20 раз (подбери 0.05–0.1)
        vx *= damping
        vy *= damping

        # === применяем импульс ===
        self.body.velocity = (vx, vy)
        self.body.angular_velocity = vx * 0.01



        