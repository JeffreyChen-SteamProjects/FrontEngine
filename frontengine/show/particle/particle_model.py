from dataclasses import dataclass

from PySide6.QtWidgets import QGraphicsPixmapItem


@dataclass
class Particle:
    """粒子資料結構 / Particle data structure"""
    x: int
    y: int
    pixmap_item: QGraphicsPixmapItem
