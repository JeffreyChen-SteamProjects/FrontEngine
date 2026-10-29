"""INK: suspicious crow with a square-round head, wedge beak, one white wing patch and orange block feet."""
from __future__ import annotations

from PySide6.QtGui import QPainterPath

from frontengine.show.pet.inkside.faces import EyeStyle, MouthStyle
from frontengine.show.pet.inkside.ink import INK, ORANGE, PAPER, Brush, line, polygon, rect, rounded
from frontengine.show.pet.inkside.template import DEFAULT_BASE, Group, Template

HEAD = rounded(-64, -52, 128, 100, 42)


def _beak(choice: str) -> QPainterPath:
    tip = {'long': 106, 'short': 80}.get(choice, 96)  # leaves room for the walk's forward glance
    return polygon((28, -10), (tip, 14), (28, 34))


def _crest(choice: str) -> list[QPainterPath]:
    if choice == 'spike':
        return [polygon((-20, -48), (-4, -100), (6, -48))]
    if choice == 'none':
        return []
    return [polygon((-24, -48), (-30, -88), (-12, -50)), polygon((-10, -48), (-2, -94), (8, -48))]


def _tail(choice: str) -> list[QPainterPath]:
    if choice == 'notch':
        return [polygon((0, -10), (-44, -26), (-34, -6), (-50, 8), (0, 10))]
    if choice == 'fan':
        return [polygon((0, -8), (-46, -30), (-40, -20), (0, 0)), polygon((0, -4), (-52, -6), (-52, 4), (0, 6)),
                polygon((0, 2), (-44, 14), (-40, 20), (0, 9))]
    return [rect(-46, -14, 46, 26)]


class Ink(Template):
    ident = 'inkside-ink'
    name = 'INK'
    template = 'inkside-bird-v1'
    palette = {'feather': INK, 'beak': ORANGE, 'patch': PAPER, 'legs': ORANGE}
    base = {**DEFAULT_BASE, 'head': (124, 132), 'tail': (104, 206)}
    crown = (-52.0, 60.0)
    chin = 48.0
    torso_region = 'feather'
    fx_region = 'beak'
    eye_centers = ((-30.0, -12.0), (16.0, -12.0))
    mouth_center = (28.0, 12.0)
    eyes = {'glance': ('Side glance', EyeStyle(34, 17, pupil='side', brow='flat')),
            'half': ('Half closed', EyeStyle(34, 17, lid=0.5)),
            'glare': ('Glare', EyeStyle(34, 15, shape='tilt', brow='glare'))}
    mouths = {'closed': ('Closed beak', MouthStyle('beak', 18)),
              'parted': ('Parted beak', MouthStyle('beak', 24))}
    eye_default, mouth_default = 'glance', 'closed'
    sprite_actions = {'walk_sprite': ('inkside-ink-walk.png', 8, 90),
                      'climb_sprite': ('inkside-ink-climb.png', 8, 110)}

    def head(self, b: Brush) -> None:
        b.fill(HEAD, 'feather')

    def head_front(self, b: Brush) -> None:
        b.outline(HEAD)

    def arm(self, b: Brush, side: str) -> None:
        """Wings replace arms; the white patch is on the character's left wing only."""
        wing = polygon((-12, -8), (12, -8), (16, 30), (4, 46), (-2, 36), (-10, 44), (-14, 28))
        b.rim(wing, 2.5)
        b.fill(wing, 'feather')
        if side == 'r':
            b.clip(wing, lambda: b.fill(rect(-20, 10, 40, 22), 'patch'))
        b.outline(wing)

    def foot(self, b: Brush, side: str) -> None:
        b.shape(rect(-4, -26, 8, 20), 'legs', 4)
        b.shape(rounded(-18, -8, 36, 16, 3), 'legs', 5)

    def extra_groups(self) -> dict[str, Group]:
        return {
            'beak': Group('Beak', 'face', 54, 'wedge', {'wedge': 'Wedge', 'long': 'Long', 'short': 'Short'},
                          self._beak),
            'crest': Group('Crest', 'head', 0, 'tuft', {'tuft': 'Tuft', 'spike': 'Spike', 'none': 'None'},
                           self._crest, ear=True),
            'tail': Group('Tail', 'tail', 10, 'square', {'square': 'Square', 'notch': 'Notched', 'fan': 'Fan'},
                          self._tail),
        }

    @staticmethod
    def _beak(b: Brush, choice: str, _context: str) -> None:
        beak = _beak(choice)
        b.shape(beak, 'beak')
        b.outline(line((40, 12), ({'long': 92, 'short': 68}.get(choice, 82), 14)), 3)

    @staticmethod
    def _crest(b: Brush, choice: str, _context: str) -> None:
        for feather in _crest(choice):
            b.shape(feather, 'feather', 5)

    @staticmethod
    def _tail(b: Brush, choice: str, _context: str) -> None:
        for feather in _tail(choice):
            b.shape(feather, 'feather', 5)
