import random
from typing import Dict, Callable

from frontengine.utils.logging.loggin_instance import front_engine_logger


def particle_down(particle_dict: Dict[str, dict], particle_speed: int = 30) -> None:
    """
    粒子向下移動
    Move particles downward
    """
    front_engine_logger.debug(f"[particle_down] speed={particle_speed}, count={len(particle_dict)}")
    for particle in particle_dict.values():
        particle["y"] = particle.get("y", 0) + random.randint(0, particle_speed)


def particle_up(particle_dict: Dict[str, dict], particle_speed: int = 30) -> None:
    """
    粒子向上移動
    Move particles upward
    """
    front_engine_logger.debug(f"[particle_up] speed={particle_speed}, count={len(particle_dict)}")
    for particle in particle_dict.values():
        particle["y"] = particle.get("y", 0) - random.randint(0, particle_speed)


def particle_left(particle_dict: Dict[str, dict], particle_speed: int = 30) -> None:
    """
    粒子向左移動
    Move particles left
    """
    front_engine_logger.debug(f"[particle_left] speed={particle_speed}, count={len(particle_dict)}")
    for particle in particle_dict.values():
        particle["x"] = particle.get("x", 0) - random.randint(0, particle_speed)


def particle_right(particle_dict: Dict[str, dict], particle_speed: int = 30) -> None:
    """
    粒子向右移動
    Move particles right
    """
    front_engine_logger.debug(f"[particle_right] speed={particle_speed}, count={len(particle_dict)}")
    for particle in particle_dict.values():
        particle["x"] = particle.get("x", 0) + random.randint(0, particle_speed)


def particle_left_down(particle_dict: Dict[str, dict], particle_speed: int = 30) -> None:
    """
    粒子向左下移動
    Move particles left and down
    """
    front_engine_logger.debug(f"[particle_left_down] speed={particle_speed}")
    particle_left(particle_dict, particle_speed)
    particle_down(particle_dict, particle_speed)


def particle_left_up(particle_dict: Dict[str, dict], particle_speed: int = 30) -> None:
    """
    粒子向左上移動
    Move particles left and up
    """
    front_engine_logger.debug(f"[particle_left_up] speed={particle_speed}")
    particle_left(particle_dict, particle_speed)
    particle_up(particle_dict, particle_speed)


def particle_right_down(particle_dict: Dict[str, dict], particle_speed: int = 30) -> None:
    """
    粒子向右下移動
    Move particles right and down
    """
    front_engine_logger.debug(f"[particle_right_down] speed={particle_speed}")
    particle_right(particle_dict, particle_speed)
    particle_down(particle_dict, particle_speed)


def particle_right_up(particle_dict: Dict[str, dict], particle_speed: int = 30) -> None:
    """
    粒子向右上移動
    Move particles right and up
    """
    front_engine_logger.debug(f"[particle_right_up] speed={particle_speed}")
    particle_right(particle_dict, particle_speed)
    particle_up(particle_dict, particle_speed)


def particle_random_minus(particle_dict: Dict[str, dict], particle_speed: int = 30) -> None:
    """
    粒子隨機往左下移動
    Move particles randomly left and down
    """
    front_engine_logger.debug(f"[particle_random_minus] speed={particle_speed}")
    for particle in particle_dict.values():
        particle["y"] = particle.get("y", 0) + random.randint(0, particle_speed)
        particle["x"] = particle.get("x", 0) - random.randint(0, particle_speed)


def particle_random_add(particle_dict: Dict[str, dict], particle_speed: int = 30) -> None:
    """
    粒子隨機往右上移動
    Move particles randomly right and up
    """
    front_engine_logger.debug(f"[particle_random_add] speed={particle_speed}")
    for particle in particle_dict.values():
        particle["y"] = particle.get("y", 0) - random.randint(0, particle_speed)
        particle["x"] = particle.get("x", 0) + random.randint(0, particle_speed)


def particle_random(particle_dict: Dict[str, dict], particle_speed: int = 30) -> None:
    """
    粒子隨機選擇一種方向移動
    Move particles in a random direction
    """
    front_engine_logger.debug(f"[particle_random] speed={particle_speed}")
    function: Callable = random.choice([
        particle_down, particle_up, particle_left, particle_right,
        particle_right_up, particle_left_down, particle_left_up, particle_right_down,
        particle_random_add, particle_random_minus
    ])
    function(particle_dict, particle_speed)