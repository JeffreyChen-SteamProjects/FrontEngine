import random
from typing import List, Callable

from frontengine.show.particle.particle_model import Particle
from frontengine.utils.logging.loggin_instance import front_engine_logger


def particle_down(particles: List[Particle], particle_speed: int = 30) -> None:
    """粒子向下移動"""
    front_engine_logger.debug(f"[particle_down] speed={particle_speed}, count={len(particles)}")
    for p in particles:
        p.y += random.randint(0, particle_speed)


def particle_up(particles: List[Particle], particle_speed: int = 30) -> None:
    """粒子向上移動"""
    front_engine_logger.debug(f"[particle_up] speed={particle_speed}, count={len(particles)}")
    for p in particles:
        p.y -= random.randint(0, particle_speed)


def particle_left(particles: List[Particle], particle_speed: int = 30) -> None:
    """粒子向左移動"""
    front_engine_logger.debug(f"[particle_left] speed={particle_speed}, count={len(particles)}")
    for p in particles:
        p.x -= random.randint(0, particle_speed)


def particle_right(particles: List[Particle], particle_speed: int = 30) -> None:
    """粒子向右移動"""
    front_engine_logger.debug(f"[particle_right] speed={particle_speed}, count={len(particles)}")
    for p in particles:
        p.x += random.randint(0, particle_speed)


def particle_left_down(particles: List[Particle], particle_speed: int = 30) -> None:
    """粒子向左下移動"""
    front_engine_logger.debug(f"[particle_left_down] speed={particle_speed}")
    particle_left(particles, particle_speed)
    particle_down(particles, particle_speed)


def particle_left_up(particles: List[Particle], particle_speed: int = 30) -> None:
    """粒子向左上移動"""
    front_engine_logger.debug(f"[particle_left_up] speed={particle_speed}")
    particle_left(particles, particle_speed)
    particle_up(particles, particle_speed)


def particle_right_down(particles: List[Particle], particle_speed: int = 30) -> None:
    """粒子向右下移動"""
    front_engine_logger.debug(f"[particle_right_down] speed={particle_speed}")
    particle_right(particles, particle_speed)
    particle_down(particles, particle_speed)


def particle_right_up(particles: List[Particle], particle_speed: int = 30) -> None:
    """粒子向右上移動"""
    front_engine_logger.debug(f"[particle_right_up] speed={particle_speed}")
    particle_right(particles, particle_speed)
    particle_up(particles, particle_speed)


def particle_random_minus(particles: List[Particle], particle_speed: int = 30) -> None:
    """粒子隨機往左下移動"""
    front_engine_logger.debug(f"[particle_random_minus] speed={particle_speed}")
    for p in particles:
        p.y += random.randint(0, particle_speed)
        p.x -= random.randint(0, particle_speed)


def particle_random_add(particles: List[Particle], particle_speed: int = 30) -> None:
    """粒子隨機往右上移動"""
    front_engine_logger.debug(f"[particle_random_add] speed={particle_speed}")
    for p in particles:
        p.y -= random.randint(0, particle_speed)
        p.x += random.randint(0, particle_speed)


def particle_random(particles: List[Particle], particle_speed: int = 30) -> None:
    """粒子隨機選擇一種方向移動"""
    front_engine_logger.debug(f"[particle_random] speed={particle_speed}")
    function: Callable = random.choice([
        particle_down, particle_up, particle_left, particle_right,
        particle_right_up, particle_left_down, particle_left_up, particle_right_down,
        particle_random_add, particle_random_minus
    ])
    function(particles, particle_speed)
