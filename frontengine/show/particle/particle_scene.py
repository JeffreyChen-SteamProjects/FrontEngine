from PySide6.QtCore import QTimer, QPoint
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QGraphicsScene

from frontengine.show.particle.particle_utils import particle_down, particle_up, particle_left, particle_right, \
    particle_left_down, particle_left_up, particle_right_down, particle_right_up, particle_random_minus, Particle, \
    particle_random_add


class ParticleGraphicScene(QGraphicsScene):

    def __init__(self, particle_pixmap: QPixmap, particle_direction: str, particle_count: int = 10,
                 particle_height: int = 100, particle_width: int = 100, opacity: float = 0.2):
        super().__init__()
        self.particle_pixmap = particle_pixmap
        self.particle_direction = particle_direction
        self.opacity = opacity
        self.particle_dict = {}
        for count in range(particle_count):
            self.particle_dict.update({
                f"particle_{count}": Particle(particle_height, particle_width, self.particle_pixmap)
            })
        self.update_function = {
            "down": particle_down,
            "up": particle_up,
            "left": particle_left,
            "right": particle_right,
            "left_down": particle_left_down,
            "left_up": particle_left_up,
            "right_down": particle_right_down,
            "right_up": particle_right_up,
            "random_minus": particle_random_minus,
            "random_add": particle_random_add,
        }.get(self.particle_direction)
        self.update_timer = QTimer()
        self.update_timer.setInterval(100)
        self.update_timer.timeout.connect(self.update_particle)
        self.update_timer.start()

    def update_particle(self):
        self.clear()
        for particle in self.particle_dict.values():
            pixmap_item = self.addPixmap(particle.pixmap)
            pixmap_item.setOpacity(self.opacity)
            pixmap_item.setPos(QPoint(particle.x, particle.y))
