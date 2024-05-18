import random
from typing import Dict

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QGraphicsPixmapItem


class Particle(object):

    def __init__(self, height: int, width: int, pixmap: QPixmap):
        self.x: int = random.randint(0, width)
        self.y: int = random.randint(0, height)
        self.pixmap: QPixmap = pixmap
        self.pixmap_item: [QGraphicsPixmapItem, None] = None


def particle_down(particle_dict: Dict[str, Particle], particle_speed: int = 30) -> None:
    for particle in particle_dict.values():
        particle.y += random.randint(0, particle_speed)


def particle_up(particle_dict: Dict[str, Particle], particle_speed: int = 30) -> None:
    for particle in particle_dict.values():
        particle.y -= random.randint(0, particle_speed)


def particle_left(particle_dict: Dict[str, Particle], particle_speed: int = 30) -> None:
    for particle in particle_dict.values():
        particle.x -= random.randint(0, particle_speed)


def particle_right(particle_dict: Dict[str, Particle], particle_speed: int = 30) -> None:
    for particle in particle_dict.values():
        particle.x += random.randint(0, particle_speed)


def particle_left_down(particle_dict: Dict[str, Particle], particle_speed: int = 30) -> None:
    particle_left(particle_dict, particle_speed)
    particle_down(particle_dict, particle_speed)


def particle_left_up(particle_dict: Dict[str, Particle], particle_speed: int = 30) -> None:
    particle_left(particle_dict, particle_speed)
    particle_up(particle_dict, particle_speed)


def particle_right_down(particle_dict: Dict[str, Particle], particle_speed: int = 30) -> None:
    particle_right(particle_dict, particle_speed)
    particle_down(particle_dict, particle_speed)


def particle_right_up(particle_dict: Dict[str, Particle], particle_speed: int = 30) -> None:
    particle_right(particle_dict, particle_speed)
    particle_up(particle_dict, particle_speed)


def particle_random_minus(particle_dict: Dict[str, Particle], particle_speed: int = 30) -> None:
    for particle in particle_dict.values():
        particle.y += random.randint(0, particle_speed)
        particle.x -= random.randint(0, particle_speed)


def particle_random_add(particle_dict: Dict[str, Particle], particle_speed: int = 30) -> None:
    for particle in particle_dict.values():
        particle.y -= random.randint(0, particle_speed)
        particle.x += random.randint(0, particle_speed)
