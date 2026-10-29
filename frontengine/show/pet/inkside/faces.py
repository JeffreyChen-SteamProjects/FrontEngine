"""Eye and mouth styles with the expressions every action needs.

An eye style is a small parameter set rather than a drawing per expression, so
each choice automatically provides open, closed (sleep and blink), happy and
squint forms. Choosing a half-closed eye style never loses the sleep reaction.
"""
from __future__ import annotations

from dataclasses import dataclass

from frontengine.show.pet.inkside.ink import Brush, ellipse, line, polygon, rect, rounded

EXPRESSIONS = ('open', 'closed', 'happy', 'squint')
MOUTHS = ('rest', 'open')


@dataclass(frozen=True)
class EyeStyle:
    width: float = 26.0
    height: float = 11.0
    shape: str = 'slot'      # slot | round | block | tilt
    pupil: str = 'vert'      # vert | dot | big | side | none
    lid: float = 0.0         # fraction of the eye covered by an ink lid
    brow: str = ''           # '' | raise | flat | glare
    droop: float = 0.0       # outer-corner drop in pixels
    ink_only: bool = False   # screen eyes: solid ink shapes on the face plate
    uneven: float = 1.0      # right/left size ratio
    wink: bool = False       # the right eye stays closed while the left is open


def _eye_path(style: EyeStyle, cx: float, cy: float, w: float, h: float, side: str):
    outer = -1 if side == 'l' else 1
    if style.shape == 'round':
        return ellipse(cx, cy, w / 2, h / 2)
    if style.shape == 'block':
        return rect(cx - w / 2, cy - h / 2, w, h)
    if style.shape == 'tilt' or style.droop:
        drop = style.droop or h * 0.8
        inner_x, outer_x = cx - outer * w / 2, cx + outer * w / 2
        return polygon((inner_x, cy - h / 2), (outer_x, cy - h / 2 + drop),
                       (outer_x, cy + h / 2 + drop * 0.4), (inner_x, cy + h / 2))
    return rounded(cx - w / 2, cy - h / 2, w, h, h / 2)


def _pupil(b: Brush, style: EyeStyle, cx: float, cy: float, w: float, h: float, side: str) -> None:
    if style.pupil == 'none':
        return
    toward = 1 if side == 'l' else -1
    if style.pupil == 'vert':
        b.solid(rect(cx + toward * w * 0.12 - 3, cy - h / 2, 6, h))
    elif style.pupil == 'dot':
        b.solid(ellipse(cx, cy, 3.5, 3.5))
    elif style.pupil == 'big':
        b.solid(rect(cx - w * 0.22, cy - h * 0.35, w * 0.44, h * 0.7))
    elif style.pupil == 'side':
        b.solid(rect(cx + w * 0.18 - 4, cy - h / 2, 8, h))


def _brow(b: Brush, style: EyeStyle, cx: float, cy: float, w: float, h: float, side: str) -> None:
    outer = -1 if side == 'l' else 1
    top = cy - h / 2 - 8
    if style.brow == 'raise' and side == 'l':
        b.mark(line((cx - w / 2, top + 2), (cx + w / 2, top - 6)), 4.5)
    elif style.brow in ('flat', 'raise'):
        b.mark(line((cx - w / 2, top + 3), (cx + w / 2, top + 3)), 4.5)
    elif style.brow == 'glare':
        b.mark(line((cx + outer * w / 2, top - 4), (cx - outer * w / 2, top + 5)), 5)


def _open_eye(b: Brush, style: EyeStyle, cx: float, cy: float, w: float, h: float, side: str) -> None:
    if style.shape == 'dots':
        for col in range(3):
            for row in range(2):
                b.solid(rect(cx - w / 2 + col * w / 3 + 1, cy - h / 2 + row * h / 2 + 1, w / 3 - 3, h / 2 - 3))
        return
    path = _eye_path(style, cx, cy, w, h, side)
    if style.ink_only:
        b.solid(path)
    else:
        b.fill(path, 'paper')
        b.clip(path, lambda: _pupil(b, style, cx, cy, w, h, side))
        if style.lid:
            b.clip(path, lambda: b.solid(rect(cx - w, cy - h / 2 - 2, w * 2, h * style.lid + 2)))
        b.outline(path, 3.5)
    _brow(b, style, cx, cy, w, h, side)


def draw_eye(b: Brush, style: EyeStyle, center: tuple[float, float], side: str, expression: str) -> None:
    cx, cy = center
    scale = style.uneven if side == 'r' else 1.0
    w, h = style.width * scale, style.height * scale
    if style.wink and side == 'r' and expression == 'open':
        expression = 'closed'
    if expression == 'open':
        _open_eye(b, style, cx, cy, w, h, side)
        return
    half = w / 2
    if expression == 'closed':
        sag = 3 + style.droop * 0.3
        b.mark(line((cx - half, cy), (cx, cy + sag), (cx + half, cy)), 4.5)
    elif expression == 'happy':
        b.mark(line((cx - half, cy + 3), (cx, cy - 6), (cx + half, cy + 3)), 5)
    else:
        point = -1 if side == 'l' else 1
        tip = cx - point * half
        b.mark(line((cx + point * half, cy - 6), (tip, cy), (cx + point * half, cy + 6)), 5)


@dataclass(frozen=True)
class MouthStyle:
    kind: str = 'line'        # line | tooth | crooked | buck | offset | grin | smirk | steps | beak | small
    width: float = 18.0


def _mouth_rest(b: Brush, style: MouthStyle, x: float, y: float) -> None:
    w = style.width
    if style.kind == 'small':
        b.solid(ellipse(x, y + 1, 4.5, 3.5))
    if style.kind in ('line', 'tooth', 'buck', 'offset'):
        b.outline(line((x - w / 2, y), (x + w / 2, y)), 4)
    if style.kind == 'tooth':
        _teeth(b, ((x + w / 2 - 7, y),))
    elif style.kind == 'buck':
        _teeth(b, ((x - 7, y), (x + 1, y)))
    elif style.kind == 'offset':
        _teeth(b, ((x - 8, y), (x + 2, y + 3)))
    elif style.kind == 'crooked':
        b.outline(line((x - w / 2, y + 2), (x - 2, y - 1), (x + 3, y + 3), (x + w / 2, y - 3)), 4)
    elif style.kind == 'smirk':
        b.outline(line((x - w / 2, y + 3), (x + w / 2, y - 3)), 4)
    elif style.kind == 'steps':
        b.outline(line((x - w / 2, y + 3), (x - w / 6, y + 3), (x - w / 6, y - 2), (x + w / 6, y - 2),
                       (x + w / 6, y + 3), (x + w / 2, y + 3)), 3.5)
    elif style.kind == 'grin':
        b.solid(polygon((x - w / 2, y - 3), (x + w / 2, y - 3), (x + w / 3, y + 4), (x - w / 3, y + 4)))
        b.fill(polygon((x + w / 2 - 9, y - 3), (x + w / 2 - 3, y - 3), (x + w / 2 - 6, y + 3)), 'paper')


def _teeth(b: Brush, points) -> None:
    for tx, ty in points:
        tooth = rect(tx, ty, 7, 8)
        b.fill(tooth, 'paper')
        b.outline(tooth, 2.5)


def draw_mouth(b: Brush, style: MouthStyle, center: tuple[float, float], expression: str) -> None:
    x, y = center
    if style.kind == 'beak':
        # The beak itself belongs to the character; the mouth choice only opens it.
        # An empty drawing becomes the transparent placeholder for a closed beak.
        if expression == 'open' or style.width > 18:
            gap = 7 if expression == 'open' else 3
            b.solid(polygon((x, y - gap), (x + 34, y), (x, y + gap)))
        return
    if expression == 'rest':
        _mouth_rest(b, style, x, y)
        return
    w = max(12.0, style.width * 0.8)
    mouth = rounded(x - w / 2, y - 5, w, 13, 6)
    b.solid(mouth)
    if style.kind in ('tooth', 'buck', 'offset', 'grin'):
        b.fill(rect(x + w / 2 - 9, y - 5, 6, 6), 'paper')
