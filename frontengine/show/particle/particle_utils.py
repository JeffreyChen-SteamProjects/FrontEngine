import random
from typing import Dict

from PySide6.QtGui import QPixmap


class Particle(object):

    def __init__(self, height: int, width: int, pixmap: QPixmap):
        self.x = random.randint(0, width)
        self.y = random.randint(0, height)
        self.pixmap = pixmap


def particle_down(particle_dict: Dict[str, Particle]) -> None:
    for particle in particle_dict.values():
        particle.y -= random.randint(0, 15)


def particle_up(particle_dict: Dict[str, Particle]) -> None:
    for particle in particle_dict.values():
        particle.y += random.randint(0, 15)


def particle_left(particle_dict: Dict[str, Particle]) -> None:
    for particle in particle_dict.values():
        particle.x -= random.randint(0, 15)


def particle_right(particle_dict: Dict[str, Particle]) -> None:
    for particle in particle_dict.values():
        particle.x += random.randint(0, 15)


def particle_left_down(particle_dict: Dict[str, Particle]) -> None:
    particle_left(particle_dict)
    particle_down(particle_dict)


def particle_left_up(particle_dict: Dict[str, Particle]) -> None:
    particle_left(particle_dict)
    particle_up(particle_dict)


def particle_right_down(particle_dict: Dict[str, Particle]) -> None:
    particle_right(particle_dict)
    particle_down(particle_dict)


def particle_right_up(particle_dict: Dict[str, Particle]) -> None:
    particle_right(particle_dict)
    particle_up(particle_dict)


def particle_random_minus(particle_dict: Dict[str, Particle]) -> None:
    for particle in particle_dict.values():
        particle.y -= random.randint(0, 15)
        particle.x -= random.randint(0, 15)


def particle_random_add(particle_dict: Dict[str, Particle]) -> None:
    for particle in particle_dict.values():
        particle.y += random.randint(0, 15)
        particle.x += random.randint(0, 15)
