from typing import Callable

from PySide6.QtCore import QTimer, QPoint, QRect
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QGraphicsScene, QWidget

from frontengine.show.particle.particle_utils import particle_down, particle_up, particle_left, particle_right, \
    particle_left_down, particle_left_up, particle_right_down, particle_right_up, particle_random_minus, Particle, \
    particle_random_add, particle_random


class ParticleGraphicScene(QGraphicsScene):

    def __init__(self, particle_pixmap: QPixmap, particle_direction: str,
                 particle_count: int = 500,
                 screen_height: int = 1920, screen_width: int = 1080, opacity: float = 0.2,
                 particle_speed: int = 1):
        super().__init__()
        self.particle_pixmap: QPixmap = particle_pixmap
        self.particle_direction: str = particle_direction
        self.particle_count: int = particle_count
        self.opacity: float = opacity
        self.particle_dict: dict = {}
        self.particle_speed: int = particle_speed
        self.screen_height: int = screen_height
        self.screen_width: int = screen_width
        self.create_particle()
        self.update_function: Callable = {
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
            "random": particle_random
        }.get(self.particle_direction)
        self.setSceneRect(QRect(0, 0, screen_width, screen_height))
        self.update_timer: QTimer = QTimer()
        self.update_timer.setInterval(10)
        self.update_timer.timeout.connect(self.update_particle)
        self.update_timer.start()

    def create_particle(self):
        self.particle_dict = {}
        for count in range(self.particle_count):
            self.particle_dict.update({
                f"particle_{count}": Particle(self.screen_height, self.screen_width, self.particle_pixmap)
            })

    def update_particle(self):
        self.clear()
        self.update_function(self.particle_dict, self.particle_speed)
        for particle_key, particle in self.particle_dict.items():
            pixmap_item = self.addPixmap(particle.pixmap)
            pixmap_item.setOpacity(self.opacity)
            pixmap_item.setPos(particle.x, particle.y)
            particle.pixmap_item = pixmap_item
            if not self.sceneRect().contains(QPoint(particle.x, particle.y)):
                self.removeItem(particle.pixmap_item)
        if len(self.items()) == 0:
            self.create_particle()
