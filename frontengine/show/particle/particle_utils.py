import random
from typing import Dict, Callable

from frontengine.utils.logging.loggin_instance import front_engine_logger


def particle_down(particle_dict: Dict[str, dict], particle_speed: int = 30) -> None:
    front_engine_logger.info("particle_utils.py particle_down "
                             f"particle_dict: {particle_dict} "
                             f"particle_speed: {particle_speed}")
    for particle in particle_dict.values():
        particle.update({"y": particle.get("y") + random.randint(0, particle_speed)})


def particle_up(particle_dict: Dict[str, dict], particle_speed: int = 30) -> None:
    front_engine_logger.info("particle_utils.py particle_up "
                             f"particle_dict: {particle_dict} "
                             f"particle_speed: {particle_speed}")
    for particle in particle_dict.values():
        particle.update({"y": particle.get("y") - random.randint(0, particle_speed)})


def particle_left(particle_dict: Dict[str, dict], particle_speed: int = 30) -> None:
    front_engine_logger.info("particle_utils.py particle_left "
                             f"particle_dict: {particle_dict} "
                             f"particle_speed: {particle_speed}")
    for particle in particle_dict.values():
        particle.update({"x": particle.get("x") - random.randint(0, particle_speed)})


def particle_right(particle_dict: Dict[str, dict], particle_speed: int = 30) -> None:
    front_engine_logger.info("particle_utils.py particle_right "
                             f"particle_dict: {particle_dict} "
                             f"particle_speed: {particle_speed}")
    for particle in particle_dict.values():
        particle.update({"x": particle.get("x") + random.randint(0, particle_speed)})


def particle_left_down(particle_dict: Dict[str, dict], particle_speed: int = 30) -> None:
    front_engine_logger.info("particle_utils.py particle_left_down "
                             f"particle_dict: {particle_dict} "
                             f"particle_speed: {particle_speed}")
    particle_left(particle_dict, particle_speed)
    particle_down(particle_dict, particle_speed)


def particle_left_up(particle_dict: Dict[str, dict], particle_speed: int = 30) -> None:
    front_engine_logger.info("particle_utils.py particle_left_up "
                             f"particle_dict: {particle_dict} "
                             f"particle_speed: {particle_speed}")
    particle_left(particle_dict, particle_speed)
    particle_up(particle_dict, particle_speed)


def particle_right_down(particle_dict: Dict[str, dict], particle_speed: int = 30) -> None:
    front_engine_logger.info("particle_utils.py particle_right_down "
                             f"particle_dict: {particle_dict} "
                             f"particle_speed: {particle_speed}")
    particle_right(particle_dict, particle_speed)
    particle_down(particle_dict, particle_speed)


def particle_right_up(particle_dict: Dict[str, dict], particle_speed: int = 30) -> None:
    front_engine_logger.info("particle_utils.py particle_right_up "
                             f"particle_dict: {particle_dict} "
                             f"particle_speed: {particle_speed}")
    particle_right(particle_dict, particle_speed)
    particle_up(particle_dict, particle_speed)


def particle_random_minus(particle_dict: Dict[str, dict], particle_speed: int = 30) -> None:
    front_engine_logger.info("particle_utils.py particle_random_minus "
                             f"particle_dict: {particle_dict} "
                             f"particle_speed: {particle_speed}")
    for particle in particle_dict.values():
        particle.update({"y": particle.get("y") + random.randint(0, particle_speed)})
        particle.update({"x": particle.get("x") - random.randint(0, particle_speed)})


def particle_random_add(particle_dict: Dict[str, dict], particle_speed: int = 30) -> None:
    front_engine_logger.info("particle_utils.py particle_random_add "
                             f"particle_dict: {particle_dict} "
                             f"particle_speed: {particle_speed}")
    for particle in particle_dict.values():
        particle.update({"y": particle.get("y") - random.randint(0, particle_speed)})
        particle.update({"x": particle.get("x") + random.randint(0, particle_speed)})


def particle_random(particle_dict: Dict[str, dict], particle_speed: int = 30) -> None:
    front_engine_logger.info("particle_utils.py particle_random "
                             f"particle_dict: {particle_dict} "
                             f"particle_speed: {particle_speed}")
    function: Callable = random.choice(
        [particle_down, particle_up, particle_left, particle_right, particle_right_up, particle_left_down,
         particle_left_up, particle_right_down, particle_random_add, particle_random_minus])
    function(particle_dict, particle_speed)
