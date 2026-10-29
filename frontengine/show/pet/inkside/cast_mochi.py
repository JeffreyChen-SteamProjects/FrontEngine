"""MOCHI: wide squat cat, one pointed and one folded ear, half-face patch, zigzag tail."""
from __future__ import annotations

from PySide6.QtCore import QPointF
from PySide6.QtGui import QPainterPath

from frontengine.show.pet.inkside.faces import EyeStyle, MouthStyle
from frontengine.show.pet.inkside.ink import INK, ORANGE, PAPER, Brush, ellipse, polygon, rect, rounded
from frontengine.show.pet.inkside.template import Group, Template

HEAD = rounded(-74, -46, 148, 90, 36)


def _patch(choice: str) -> QPainterPath:
    if choice == 'eye':
        return ellipse(36, -4, 30, 26)
    if choice == 'split':
        return polygon((10, -60), (90, -60), (90, 60), (40, 60))
    path = QPainterPath(QPointF(6, -60))
    path.cubicTo(QPointF(-4, -20), QPointF(18, 10), QPointF(4, 60))
    path.lineTo(QPointF(90, 60))
    path.lineTo(QPointF(90, -60))
    path.closeSubpath()
    return path


def _folded_ear(choice: str) -> QPainterPath:
    if choice == 'up':
        return polygon((18, -40), (52, -98), (70, -38))
    if choice == 'droop':
        return polygon((22, -42), (60, -66), (98, -40), (82, -24))
    return polygon((18, -42), (50, -84), (88, -74), (76, -44))


def _tail(choice: str) -> QPainterPath:
    if choice == 'stub':
        return polygon((-6, 4), (22, -10), (14, -26), (40, -34), (46, -24), (26, -16), (34, 0), (6, 14))
    if choice == 'hook':
        return polygon((-6, 4), (26, -12), (16, -36), (46, -48), (60, -78), (72, -72), (58, -40),
                       (30, -30), (40, -6), (6, 14))
    return polygon((-6, 4), (26, -12), (14, -38), (44, -52), (34, -80), (52, -84), (64, -48),
                   (32, -32), (42, -6), (6, 14))


class Mochi(Template):
    ident = 'inkside-mochi'
    name = 'MOCHI'
    template = 'inkside-cat-v1'
    palette = {'fur': PAPER, 'mark': INK, 'coat': ORANGE, 'accent': ORANGE, 'band': ORANGE}
    eyes = {'narrow': ('Narrow', EyeStyle(28, 11)),
            'droopy': ('Droopy', EyeStyle(26, 12, droop=5, pupil='dot')),
            'brow': ('Raised brow', EyeStyle(26, 11, brow='raise'))}
    mouths = {'tooth': ('Square tooth', MouthStyle('tooth', 20)),
              'crooked': ('Crooked', MouthStyle('crooked', 20)),
              'line': ('Short line', MouthStyle('line', 14))}
    eye_default, mouth_default = 'narrow', 'tooth'
    sprite_actions = {'walk_sprite': ('inkside-mochi-walk.png', 8, 90),
                      'climb_sprite': ('inkside-mochi-climb.png', 8, 110)}

    def head(self, b: Brush) -> None:
        b.fill(HEAD, 'fur')

    def head_front(self, b: Brush) -> None:
        for x in (-50, 50):
            b.fill(ellipse(x, 20, 13, 11), 'accent')
        b.fill(polygon((-7, 9), (7, 9), (0, 17)), 'accent')
        b.outline(HEAD)

    def ears(self, b: Brush) -> None:
        ear = polygon((-72, -34), (-58, -104), (-16, -44))
        b.shape(ear, 'accent')
        b.solid(polygon((-72, -34), (-58, -104), (-50, -60), (-44, -40)))
        b.outline(ear)

    def extra_groups(self) -> dict[str, Group]:
        return {
            'patch': Group('Face patch', 'face', 51, 'half',
                           {'half': 'Half face', 'eye': 'Eye ring', 'split': 'Split'},
                           lambda b, choice, _: b.clip(HEAD, lambda: b.fill(_patch(choice), 'mark'))),
            'ear': Group('Folded ear', 'head', 0, 'fold', {'fold': 'Folded', 'droop': 'Drooping', 'up': 'Upright'},
                         self._ear, ear=True),
            'tail': Group('Tail tip', 'tail', 10, 'bolt', {'bolt': 'Lightning', 'hook': 'Hook', 'stub': 'Stub'},
                          self._tail),
        }

    @staticmethod
    def _ear(b: Brush, choice: str, _context: str) -> None:
        shape = _folded_ear(choice)
        b.fill(shape, 'mark')
        inner = {'fold': ((30, -46), (50, -74), (62, -46)), 'droop': ((36, -42), (60, -60), (74, -40)),
                 'up': ((30, -42), (51, -84), (60, -42))}[choice]
        b.fill(polygon(*inner), 'accent')
        b.outline(shape)

    @staticmethod
    def _tail(b: Brush, choice: str, _context: str) -> None:
        shape = _tail(choice)
        b.fill(shape, 'mark')
        b.clip(shape, lambda: b.fill(rect(-20, -34, 120, 14), 'band'))
        b.outline(shape, 5)
