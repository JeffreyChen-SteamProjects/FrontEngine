"""GILL: slow axolotl with a wide capsule head, three orange gills a side, square blush and a paddle tail."""
from __future__ import annotations

from PySide6.QtGui import QPainterPath, QTransform

from frontengine.show.pet.inkside.faces import EyeStyle, MouthStyle
from frontengine.show.pet.inkside.ink import ORANGE, PAPER, Brush, ellipse, line, polygon, rect, rounded
from frontengine.show.pet.inkside.template import DEFAULT_BASE, Group, Template

HEAD = rounded(-82, -42, 164, 84, 42)


def _gill(choice: str, angle: float) -> QPainterPath:
    if choice == 'round':
        stalk = rounded(0, -6, 24, 12, 3).united(ellipse(27, 0, 8, 8))
    elif choice == 'fork':
        stalk = polygon((0, -6), (22, -6), (32, -13), (29, 0), (32, 13), (22, 6), (0, 6))
    else:
        stalk = rect(0, -7, 32, 14)
    return QTransform().rotate(angle).map(stalk)


def _tail(choice: str) -> QPainterPath:
    if choice == 'round':
        return ellipse(26, -14, 26, 22)
    if choice == 'fin':
        return polygon((-4, 6), (20, -30), (58, -40), (44, -18), (60, 0), (20, 14))
    path = QPainterPath()
    path.addEllipse(0, -44, 54, 54)
    return path.united(rect(-6, -10, 24, 18))


class Gill(Template):
    ident = 'inkside-gill'
    name = 'GILL'
    template = 'inkside-axolotl-v1'
    palette = {'skin': PAPER, 'gill': ORANGE, 'blush': ORANGE, 'tail': ORANGE}
    base = {**DEFAULT_BASE, 'head': (128, 128), 'tail': (148, 214)}
    crown = (-42.0, 60.0)
    chin = 42.0
    torso_region = 'skin'
    fx_region = 'gill'
    eye_centers = ((-44.0, -4.0), (44.0, -4.0))
    mouth_center = (0.0, 14.0)
    eyes = {'small': ('Small squares', EyeStyle(9, 11, shape='block', ink_only=True)),
            'droop': ('Droopy', EyeStyle(14, 9, droop=4, ink_only=True)),
            'blink': ('Winking', EyeStyle(9, 11, shape='block', ink_only=True, wink=True))}
    mouths = {'tooth': ('Flat with tooth', MouthStyle('tooth', 26)),
              'small': ('Small open', MouthStyle('small', 10))}
    eye_default, mouth_default = 'small', 'tooth'
    sprite_actions = {'walk_sprite': ('inkside-gill-walk.png', 8, 90),
                      'climb_sprite': ('inkside-gill-climb.png', 8, 110)}

    def nudge(self, part: str, pose) -> tuple[int, int]:
        # The capsule head and gills are too wide to slide left when lying down.
        return (16, 0) if pose.torso == 'lie' and part in ('head', 'neck', 'arm_l', 'arm_r') else (0, 0)

    def head(self, b: Brush) -> None:
        b.fill(HEAD, 'skin')

    def head_front(self, b: Brush) -> None:
        b.outline(HEAD)

    def extra_groups(self) -> dict[str, Group]:
        return {
            'gills': Group('Gill tips', 'head', 0, 'bar', {'bar': 'Bars', 'round': 'Round', 'fork': 'Forked'},
                           self._gills, ear=True),
            'blush': Group('Blush', 'face', 53, 'square', {'square': 'Square', 'round': 'Round', 'line': 'Lines'},
                           self._blush),
            'tail': Group('Tail', 'tail', 10, 'paddle', {'paddle': 'Paddle', 'round': 'Round', 'fin': 'Fin'},
                          lambda b, choice, _: b.shape(_tail(choice), 'tail')),
        }

    @staticmethod
    def _gills(b: Brush, choice: str, _context: str) -> None:
        for angle, (x, y) in ((-150, (-70, -22)), (180, (-78, 0)), (150, (-70, 22))):
            for side in (1, -1):
                gill = _gill(choice, angle if side == 1 else 180 - angle).translated(x * side, y)
                b.shape(gill, 'gill', 5)

    @staticmethod
    def _blush(b: Brush, choice: str, _context: str) -> None:
        for x in (-60, 60):
            if choice == 'round':
                b.fill(ellipse(x, 16, 11, 9), 'blush')
            elif choice == 'line':
                for dx in (-6, 0, 6):
                    b.outline(line((x + dx + 2, 10), (x + dx - 2, 20)), 3)
            else:
                b.fill(rect(x - 11, 8, 22, 15), 'blush')
