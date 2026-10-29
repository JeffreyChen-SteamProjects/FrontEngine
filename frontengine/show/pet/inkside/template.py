"""The drawing contract every INKSIDE body type fulfils.

Coordinates are local to a part's pivot: the head is drawn around the head
pivot, the torso around the body pivot, an arm hangs down from its shoulder.
The builder places and rotates these drawings for each frame, and garments use
the same metrics (crown, neck, torso outline) so they fit every pose.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import QPointF
from PySide6.QtGui import QPainterPath

from frontengine.show.pet.inkside.faces import EyeStyle, MouthStyle, draw_eye, draw_mouth
from frontengine.show.pet.inkside.ink import ORANGE, PAPER, INK, Brush, ellipse, polygon, rounded

DEFAULT_BASE = {
    'head': (128, 124), 'neck': (128, 166), 'body': (128, 194), 'tail': (150, 210),
    'arm_l': (93, 172), 'arm_r': (163, 172), 'foot_l': (105, 234), 'foot_r': (151, 234),
}


@dataclass(frozen=True)
class Group:
    """A character part group: one drawing per choice, attached to one part."""
    name: str
    part: str
    z: int
    default: str
    choices: dict[str, str]
    draw: Callable[[Brush, str, str], None]
    ear: bool = False


def pear(top_w: float, bottom_w: float, top: float, bottom: float) -> QPainterPath:
    """A soft pear torso: narrow shoulders, wide seat, flat base."""
    path = QPainterPath(QPointF(-top_w / 2, top))
    path.quadTo(QPointF(0, top - 8), QPointF(top_w / 2, top))
    path.cubicTo(QPointF(bottom_w / 2 + 4, top + (bottom - top) * 0.45),
                 QPointF(bottom_w / 2 + 2, bottom), QPointF(bottom_w / 2 - 10, bottom))
    path.lineTo(QPointF(-bottom_w / 2 + 10, bottom))
    path.cubicTo(QPointF(-bottom_w / 2 - 2, bottom), QPointF(-bottom_w / 2 - 4, top + (bottom - top) * 0.45),
                 QPointF(-top_w / 2, top))
    path.closeSubpath()
    return path


class Template:
    ident = ''
    name = ''
    template = ''
    palette: dict[str, str] = {}
    base = DEFAULT_BASE
    crown = (-46.0, 74.0)            # head top (y) and half width, head-local
    chin = 44.0                      # head bottom (y), head-local; neckwear hangs below it
    eye_centers = ((-34.0, -4.0), (34.0, -4.0))
    mouth_center = (0.0, 22.0)
    eyes: dict[str, tuple[str, EyeStyle]] = {}
    mouths: dict[str, tuple[str, MouthStyle]] = {}
    eye_default = ''
    mouth_default = ''
    torso_region = 'coat'
    fx_origin = (0.0, -60.0)
    # Generated whole-body frames: {'walk_sprite': (atlas file in sprites/, frames, ms per frame)}.
    sprite_actions: dict = {}
    fx_region = 'accent'

    # --- body parts -------------------------------------------------------
    def head(self, b: Brush) -> None:
        raise NotImplementedError

    def head_front(self, b: Brush) -> None:
        """Head details drawn above face patches: cheeks, nose and the outline."""

    def ears(self, b: Brush) -> None:
        """Appendages above the crown; drawn behind the head and again over hats."""

    def torso(self, kind: str) -> QPainterPath:
        if kind == 'lie':
            return ellipse(0, 22, 74, 22)
        if kind == 'sit':
            return pear(64, 90, -26, 38)
        return pear(56, 80, -34, 38)

    def body(self, b: Brush, kind: str) -> None:
        b.shape(self.torso(kind), self.torso_region)

    def arm(self, b: Brush, side: str) -> None:
        paw = rounded(-10, -6, 20, 44, 10)
        b.rim(paw, 2.5)
        b.shape(paw, 'ink')

    def foot(self, b: Brush, side: str) -> None:
        b.shape(ellipse(0, 0, 25, 11), 'ink')

    def tail(self, b: Brush) -> None:
        """Default: no tail (a tail group may draw it instead)."""

    def extra_groups(self) -> dict[str, Group]:
        return {}

    def nudge(self, part: str, pose) -> tuple[int, int]:
        """A body-specific correction to the shared poses; garments receive it too."""
        return 0, 0

    # --- face -------------------------------------------------------------
    def groups(self) -> dict[str, Group]:
        eyes = Group('Eyes', 'face', 57, self.eye_default, {k: v[0] for k, v in self.eyes.items()},
                     lambda b, choice, expression: self.draw_eyes(b, choice, expression))
        mouth = Group('Mouth', 'face', 58, self.mouth_default, {k: v[0] for k, v in self.mouths.items()},
                      lambda b, choice, expression: draw_mouth(b, self.mouths[choice][1], self.mouth_center,
                                                               'open' if expression == 'open' else 'rest'))
        return {'eyes': eyes, 'mouth': mouth, **self.extra_groups()}

    def draw_eyes(self, b: Brush, choice: str, expression: str) -> None:
        style = self.eyes[choice][1]
        draw_eye(b, style, self.eye_centers[0], 'l', expression)
        draw_eye(b, style, self.eye_centers[1], 'r', expression)

    # --- effects ----------------------------------------------------------
    def fx(self, b: Brush, name: str) -> None:
        """Small authored reaction effects, drawn relative to the head pivot."""
        x, y = self.fx_origin
        if name.startswith('heart_'):
            step = int(name[-1])
            _heart(b, x + 70 + step * 3, y - 6 - step * 9, 1.0 - step * 0.08, self.fx_region)
        elif name in ('zzz', 'zzz_small'):
            _zzz(b, x + 78, y + 6, 1.0 if name == 'zzz' else 0.7)
        elif name in ('sparkle', 'sparkle_big'):
            size = 1.3 if name == 'sparkle_big' else 1.0
            _spark(b, x - 84, y - 8, size, self.fx_region)
            _spark(b, x + 84, y - 18, size * 0.8, self.fx_region)
        elif name == 'sweat':
            drop = QPainterPath(QPointF(x + 80, y + 20))
            drop.quadTo(QPointF(x + 92, y + 40), QPointF(x + 80, y + 44))
            drop.quadTo(QPointF(x + 68, y + 40), QPointF(x + 80, y + 20))
            b.shape(drop, 'paper', 3.5)
        elif name == 'note':
            b.solid(ellipse(x + 78, y + 2, 7, 5))
            b.outline(polygon((x + 84, y + 2), (x + 84, y - 22), (x + 94, y - 16)), 4)
        elif name in ('ball_high', 'ball_hold'):
            by = y - 30 if name == 'ball_high' else y - 6
            b.shape(ellipse(x, by, 15, 15), 'paper', 4.5)
            b.clip(ellipse(x, by, 15, 15), lambda: b.solid(polygon((x - 16, by - 2), (x + 16, by - 8),
                                                                   (x + 16, by + 2), (x - 16, by + 8))))


def _heart(b: Brush, x: float, y: float, size: float, region: str) -> None:
    path = QPainterPath(QPointF(x, y + 12 * size))
    path.cubicTo(QPointF(x - 16 * size, y), QPointF(x - 10 * size, y - 13 * size), QPointF(x, y - 5 * size))
    path.cubicTo(QPointF(x + 10 * size, y - 13 * size), QPointF(x + 16 * size, y), QPointF(x, y + 12 * size))
    b.shape(path, region, 4)


def _zzz(b: Brush, x: float, y: float, size: float) -> None:
    for dx, dy, scale in ((0, 0, 1.0), (16, -18, 0.75)):
        w = 14 * scale * size
        b.outline(_zigzag(x + dx, y + dy, w), 4)


def _zigzag(x: float, y: float, w: float) -> QPainterPath:
    path = QPainterPath(QPointF(x, y))
    path.lineTo(QPointF(x + w, y))
    path.lineTo(QPointF(x, y + w))
    path.lineTo(QPointF(x + w, y + w))
    return path


def _spark(b: Brush, x: float, y: float, size: float, region: str) -> None:
    r, k = 12 * size, 3 * size
    star = polygon((x, y - r), (x + k, y - k), (x + r, y), (x + k, y + k), (x, y + r), (x - k, y + k),
                   (x - r, y), (x - k, y - k))
    b.shape(star, region, 3)


__all__ = ['Template', 'Group', 'pear', 'ORANGE', 'PAPER', 'INK']
