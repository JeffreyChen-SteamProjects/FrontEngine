"""MOSS: worried rabbit with a trapezoid face, notched leaf ears, buck teeth and a square tail puff."""
from __future__ import annotations

from PySide6.QtCore import QPointF
from PySide6.QtGui import QPainterPath

from frontengine.show.pet.inkside.faces import EyeStyle, MouthStyle
from frontengine.show.pet.inkside.ink import ORANGE, PAPER, Brush, ellipse, polygon, rounded
from frontengine.show.pet.inkside.template import DEFAULT_BASE, Group, Template


def _face() -> QPainterPath:
    path = QPainterPath(QPointF(-50, -40))
    path.lineTo(QPointF(50, -40))
    path.quadTo(QPointF(62, -40), QPointF(68, -28))
    path.lineTo(QPointF(84, 26))
    path.quadTo(QPointF(88, 42), QPointF(70, 42))
    path.lineTo(QPointF(-70, 42))
    path.quadTo(QPointF(-88, 42), QPointF(-84, 26))
    path.lineTo(QPointF(-68, -28))
    path.quadTo(QPointF(-62, -40), QPointF(-50, -40))
    path.closeSubpath()
    return path


FACE = _face()


def _upright(choice: str) -> QPainterPath:
    if choice == 'plain':
        return polygon((-56, -34), (-62, -104), (-40, -108), (-22, -38))
    if choice == 'double':
        return polygon((-56, -34), (-62, -104), (-46, -92), (-48, -104), (-34, -96), (-36, -108),
                       (-22, -38))
    return polygon((-56, -34), (-62, -108), (-46, -96), (-44, -110), (-22, -38))


def _folded(choice: str) -> QPainterPath:
    if choice == 'down':
        return polygon((20, -38), (44, -82), (78, -60), (90, -14), (72, -20), (64, -54), (42, -36))
    if choice == 'up':
        return polygon((22, -38), (40, -100), (64, -108), (80, -96), (54, -84), (46, -36))
    return polygon((20, -38), (42, -94), (66, -92), (104, -56), (84, -48), (60, -72), (46, -36))


def _tail(choice: str) -> QPainterPath:
    if choice == 'leaf':
        return polygon((0, -10), (24, -26), (38, -6), (24, 14), (0, 8))
    if choice == 'round':
        return ellipse(16, 0, 16, 15)
    return rounded(0, -14, 30, 28, 4)


class Moss(Template):
    ident = 'inkside-moss'
    name = 'MOSS'
    template = 'inkside-rabbit-v1'
    palette = {'fur': PAPER, 'leaf': ORANGE, 'coat': ORANGE, 'accent': ORANGE, 'puff': PAPER}
    base = {**DEFAULT_BASE, 'head': (128, 134), 'tail': (154, 214)}
    crown = (-40.0, 66.0)
    chin = 42.0
    eye_centers = ((-34.0, 0.0), (34.0, 0.0))
    mouth_center = (0.0, 24.0)
    eyes = {'alert': ('Alert', EyeStyle(26, 13, brow='flat')),
            'half': ('Half closed', EyeStyle(28, 12, lid=0.5, brow='flat')),
            'side': ('Side glance', EyeStyle(28, 12, pupil='side'))}
    mouths = {'buck': ('Buck teeth', MouthStyle('buck', 16)),
              'offset': ('Crooked teeth', MouthStyle('offset', 16))}
    eye_default, mouth_default = 'alert', 'buck'
    sprite_actions = {'walk_sprite': ('inkside-moss-walk.png', 8, 90),
                      'climb_sprite': ('inkside-moss-climb.png', 8, 110)}

    def head(self, b: Brush) -> None:
        b.fill(FACE, 'fur')
        b.clip(FACE, lambda: b.fill(polygon((-90, -50), (90, -50), (90, -20), (30, -14), (-90, -26)), 'leaf'))

    def head_front(self, b: Brush) -> None:
        for x in (-56, 56):
            b.fill(ellipse(x, 24, 13, 11), 'accent')
        b.fill(polygon((-6, 12), (6, 12), (0, 19)), 'accent')
        b.outline(FACE)

    def extra_groups(self) -> dict[str, Group]:
        return {
            'notch': Group('Leaf ear', 'head', 0, 'notch', {'notch': 'Notched', 'double': 'Twice notched',
                                                            'plain': 'Smooth'},
                           lambda b, choice, _: b.shape(_upright(choice), 'leaf'), ear=True),
            'fold': Group('Folded ear', 'head', 0, 'over', {'over': 'Folded over', 'down': 'Hanging',
                                                            'up': 'Half up'},
                          lambda b, choice, _: b.shape(_folded(choice), 'leaf'), ear=True),
            'tail': Group('Tail puff', 'tail', 10, 'square', {'square': 'Square', 'leaf': 'Leaf', 'round': 'Round'},
                          lambda b, choice, _: b.shape(_tail(choice), 'puff')),
        }

    def torso(self, kind: str) -> QPainterPath:
        if kind == 'stand':
            return rounded(-28, -34, 56, 72, 18)
        return super().torso(kind)
