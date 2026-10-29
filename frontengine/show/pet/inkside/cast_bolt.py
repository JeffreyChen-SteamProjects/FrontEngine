"""BOLT: earnest robot with an orange-framed screen head, offset antenna, round chest light and block boots."""
from __future__ import annotations

from PySide6.QtCore import QPointF
from PySide6.QtGui import QPainterPath

from frontengine.show.pet.inkside.faces import EyeStyle, MouthStyle
from frontengine.show.pet.inkside.ink import INK, ORANGE, PAPER, Brush, ellipse, line, polygon, rect, rounded, stroked
from frontengine.show.pet.inkside.template import DEFAULT_BASE, Group, Template


def _frame(choice: str) -> tuple[QPainterPath, QPainterPath]:
    if choice == 'square':
        return rounded(-76, -48, 152, 92, 8), rounded(-58, -32, 116, 60, 4)
    if choice == 'visor':
        outer = QPainterPath(QPointF(-76, -20))
        outer.quadTo(QPointF(-76, -48), QPointF(-44, -48))
        outer.lineTo(QPointF(44, -48))
        outer.quadTo(QPointF(76, -48), QPointF(76, -20))
        outer.lineTo(QPointF(64, 44))
        outer.lineTo(QPointF(-64, 44))
        outer.closeSubpath()
        return outer, rounded(-60, -30, 120, 40, 18)
    return rounded(-76, -48, 152, 92, 26), rounded(-58, -32, 116, 60, 12)


def _antenna_tip(choice: str) -> QPainterPath:
    if choice == 'ball':
        return ellipse(46, -90, 11, 11)
    if choice == 'bolt':
        return polygon((40, -104), (56, -104), (48, -92), (58, -92), (40, -74), (44, -88), (36, -88))
    return rounded(36, -102, 22, 20, 3)


class Bolt(Template):
    ident = 'inkside-bolt'
    name = 'BOLT'
    template = 'inkside-robot-v1'
    palette = {'frame': ORANGE, 'screen': PAPER, 'shell': INK, 'light': PAPER, 'boots': ORANGE}
    base = {**DEFAULT_BASE, 'head': (128, 126)}
    crown = (-48.0, 74.0)
    torso_region = 'shell'
    fx_region = 'frame'
    eye_centers = ((-28.0, -8.0), (30.0, -8.0))
    mouth_center = (0.0, 14.0)
    eyes = {'uneven': ('Uneven squares', EyeStyle(30, 18, shape='block', ink_only=True, uneven=0.72)),
            'bars': ('Bars', EyeStyle(30, 9, shape='block', ink_only=True)),
            'dots': ('Dot matrix', EyeStyle(27, 18, shape='dots', ink_only=True))}
    mouths = {'line': ('Short dash', MouthStyle('line', 14)),
              'steps': ('Steps', MouthStyle('steps', 24))}
    eye_default, mouth_default = 'uneven', 'line'

    def head(self, b: Brush) -> None:
        """The frame is a part choice, so the fixed head only has the ear pods."""

    def ears(self, b: Brush) -> None:
        for x in (-80, 80):
            pod = rounded(x - 12, -26, 24, 46, 10)
            b.shape(pod, 'frame')

    def foot(self, b: Brush, side: str) -> None:
        b.shape(rounded(-22, -12, 44, 22, 4), 'boots')

    def body(self, b: Brush, kind: str) -> None:
        b.shape(self.torso(kind), 'shell')

    def extra_groups(self) -> dict[str, Group]:
        return {
            'frame': Group('Face frame', 'face', 50, 'round', {'round': 'Rounded', 'square': 'Square',
                                                              'visor': 'Visor'}, self._frame),
            'antenna': Group('Antenna', 'head', 0, 'square', {'square': 'Square', 'ball': 'Ball',
                                                             'bolt': 'Lightning'}, self._antenna, ear=True),
            'chest': Group('Chest light', 'body', 32, 'circle', {'circle': 'Circle', 'bolt': 'Lightning',
                                                                'grid': 'Grid'}, self._chest),
        }

    @staticmethod
    def _frame(b: Brush, choice: str, _context: str) -> None:
        outer, screen = _frame(choice)
        b.fill(outer, 'frame')
        b.shape(screen, 'screen', 4)
        b.outline(outer)

    @staticmethod
    def _antenna(b: Brush, choice: str, _context: str) -> None:
        b.shape(stroked(line((30, -46), (46, -84)), 7), 'shell', 3)
        b.shape(_antenna_tip(choice), 'frame')

    @staticmethod
    def _chest(b: Brush, choice: str, context: str) -> None:
        y = 22 if context == 'lie' else 4
        if choice == 'bolt':
            b.shape(polygon((-4, y - 18), (12, y - 18), (4, y - 4), (14, y - 4), (-6, y + 18), (-2, y + 2),
                            (-12, y + 2)), 'light', 4)
        elif choice == 'grid':
            for dx in (-10, 3):
                for dy in (-10, 3):
                    b.shape(rect(dx, y + dy, 9, 9), 'light', 3)
        else:
            b.shape(ellipse(0, y, 17, 17), 'light', 4)
