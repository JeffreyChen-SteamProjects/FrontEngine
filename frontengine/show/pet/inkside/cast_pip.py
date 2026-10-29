"""PIP: self-important little dragon with a black hexagon head, orange snout, short horns and an arrow tail."""
from __future__ import annotations

from PySide6.QtCore import QPointF
from PySide6.QtGui import QPainterPath, QTransform

from frontengine.show.pet.inkside.faces import EyeStyle, MouthStyle
from frontengine.show.pet.inkside.ink import INK, ORANGE, PAPER, Brush, ellipse, line, polygon, stroked
from frontengine.show.pet.inkside.template import DEFAULT_BASE, Group, Template

HEAD = polygon((-44, -48), (44, -48), (76, -4), (54, 40), (-54, 40), (-76, -4))
SNOUT = polygon((-80, 2), (0, -2), (80, 2), (62, 46), (-62, 46))


def _horns(choice: str) -> list[QPainterPath]:
    shapes = {'short': ((-48, -44), (-44, -78), (-22, -48)),
              'curved': ((-50, -44), (-60, -70), (-46, -88), (-40, -70), (-24, -48)),
              'nub': ((-46, -44), (-40, -64), (-26, -64), (-22, -46))}[choice]
    return [polygon(*shapes), polygon(*((-x, y) for x, y in shapes))]


def _wing(choice: str) -> QPainterPath:
    if choice == 'round':
        points = ((-24, -20), (-60, -34), (-70, -10), (-54, 6), (-24, 4))
    elif choice == 'spiky':
        points = ((-24, -20), (-70, -40), (-58, -22), (-76, -14), (-58, -6), (-68, 6), (-24, 4))
    else:
        points = ((-24, -20), (-64, -36), (-56, -20), (-68, -8), (-52, -4), (-58, 8), (-24, 4))
    return polygon(*points)


def _tip(choice: str) -> QPainterPath:
    if choice == 'heart':
        path = QPainterPath(QPointF(78, -78))
        path.cubicTo(QPointF(62, -86), QPointF(64, -106), QPointF(78, -100))
        path.cubicTo(QPointF(90, -110), QPointF(100, -92), QPointF(78, -78))
        return path
    if choice == 'spade':
        return polygon((66, -78), (80, -108), (96, -82), (82, -78), (86, -70), (74, -70), (78, -78))
    return polygon((62, -74), (86, -104), (96, -70), (80, -76))


class Pip(Template):
    ident = 'inkside-pip'
    name = 'PIP'
    template = 'inkside-dragon-v1'
    palette = {'hide': INK, 'snout': ORANGE, 'horn': PAPER, 'belly': PAPER, 'wing': ORANGE, 'tip': ORANGE}
    base = {**DEFAULT_BASE, 'head': (128, 128), 'tail': (148, 218)}
    crown = (-48.0, 60.0)
    chin = 40.0
    torso_region = 'hide'
    fx_region = 'snout'
    eye_centers = ((-30.0, -14.0), (30.0, -14.0))
    mouth_center = (0.0, 22.0)
    eyes = {'provoke': ('Provoking', EyeStyle(28, 12, shape='tilt', brow='glare')),
            'sleepy': ('Sleepy', EyeStyle(28, 12, lid=0.55)),
            'surprised': ('Surprised', EyeStyle(20, 18, shape='round', pupil='dot'))}
    mouths = {'grin': ('Toothy grin', MouthStyle('grin', 26)),
              'smirk': ('Closed smirk', MouthStyle('smirk', 18))}
    eye_default, mouth_default = 'provoke', 'grin'
    sprite_actions = {'walk_sprite': ('inkside-pip-walk.png', 8, 90),
                      'climb_sprite': ('inkside-pip-climb.png', 8, 110)}

    def head(self, b: Brush) -> None:
        b.fill(HEAD, 'hide')
        b.clip(HEAD, lambda: b.fill(SNOUT, 'snout'))

    def head_front(self, b: Brush) -> None:
        b.outline(line((-14, 8), (-8, 12)), 3.5)
        b.outline(line((14, 8), (8, 12)), 3.5)
        b.outline(HEAD)

    def body(self, b: Brush, kind: str) -> None:
        torso = self.torso(kind)
        b.fill(torso, 'hide')
        belly = ellipse(0, 26, 50, 14) if kind == 'lie' else ellipse(0, 8, 24, 26)
        b.clip(torso, lambda: b.fill(belly, 'belly'))
        b.outline(belly, 4)
        b.outline(torso)

    def foot(self, b: Brush, side: str) -> None:
        foot = ellipse(0, 0, 24, 11)
        b.rim(foot, 2.5)
        b.shape(foot, 'ink')
        for x in (-12, 0, 12):
            b.fill(polygon((x - 4, 8), (x, -1), (x + 4, 8)), 'paper')

    def extra_groups(self) -> dict[str, Group]:
        return {
            'horns': Group('Horns', 'head', 0, 'short', {'short': 'Short', 'curved': 'Curved', 'nub': 'Nubs'},
                           self._horns, ear=True),
            'wings': Group('Wings', 'body', 12, 'bat', {'bat': 'Bat', 'round': 'Round', 'spiky': 'Spiky'},
                           self._wings),
            'tail': Group('Tail tip', 'tail', 10, 'arrow', {'arrow': 'Arrow', 'heart': 'Heart', 'spade': 'Spade'},
                          self._tail),
        }

    @staticmethod
    def _horns(b: Brush, choice: str, _context: str) -> None:
        for horn in _horns(choice):
            b.shape(horn, 'horn')

    @staticmethod
    def _wings(b: Brush, choice: str, context: str) -> None:
        if context == 'lie':
            return
        left = _wing(choice)
        b.shape(left, 'wing')
        b.shape(polygon(*((-left.elementAt(i).x, left.elementAt(i).y)
                          for i in range(left.elementCount() - 1))), 'wing')

    @staticmethod
    def _tail(b: Brush, choice: str, _context: str) -> None:
        body = QPainterPath(QPointF(-6, 0))
        body.cubicTo(QPointF(40, 10), QPointF(60, -20), QPointF(76, -80))
        shrink = QTransform().scale(0.8, 0.8)
        b.shape(shrink.map(stroked(body, 20)), 'hide')
        b.shape(shrink.map(_tip(choice)), 'tip')
