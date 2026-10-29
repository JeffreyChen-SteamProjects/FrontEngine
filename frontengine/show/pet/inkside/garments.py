"""The INKSIDE wardrobe: fourteen outfits split into wearable slot pieces.

Pieces are drawn from the template's own geometry - crown, chin and torso
outline - so one drawing fits every pose and every body type: torso garments
are clipped to the current torso shape, hats sit on the crown under the ears.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import QPointF
from PySide6.QtGui import QPainterPath

from frontengine.show.pet.inkside.ink import INK, ORANGE, PAPER, Brush, ellipse, line, polygon, rect, rounded
from frontengine.show.pet.inkside.template import Template

HAT_Z, NECK_Z, BODY_Z, STRAP_Z, BACK_Z = 60, 49, 33, 37, 14


@dataclass(frozen=True)
class Piece:
    part: str          # 'head' pieces rotate with the head; 'body' pieces follow the torso
    z: int
    draw: Callable[[Brush, Template, str], None]


@dataclass(frozen=True)
class Garment:
    ident: str
    outfit: str
    name: str
    slots: tuple[str, ...]
    palette: dict
    pieces: tuple[Piece, ...]


def _crown(t: Template) -> tuple[float, float]:
    return t.crown


def _hat(b: Brush, path: QPainterPath, region: str, width: float = 6.0) -> None:
    """Hats get a paper knockout so a black hat still reads on a black head."""
    b.rim(path, 2.5, width)
    b.shape(path, region, width)


def _chin(t: Template) -> float:
    return t.chin


# --- hats ---------------------------------------------------------------------
def _work_cap(b: Brush, t: Template, _kind: str) -> None:
    top, hw = _crown(t)
    cap = polygon((-hw * 0.7, top + 10), (-hw * 0.56, top - 22), (hw * 0.34, top - 30), (hw * 0.5, top + 2))
    _hat(b, cap, 'cloth')
    b.outline(line((-hw * 0.63, top - 6), (hw * 0.42, top - 14)), 4)


def _beret(b: Brush, t: Template, _kind: str) -> None:
    top, hw = _crown(t)
    _hat(b, ellipse(-hw * 0.12, top - 6, hw * 0.74, 21), 'cloth')
    _hat(b, rect(-hw * 0.12 - 7, top - 38, 14, 13), 'trim', 4)


def _rain_hood(b: Brush, t: Template, _kind: str) -> None:
    top, hw = _crown(t)
    hood = QPainterPath(QPointF(-hw - 6, top + 26))
    hood.quadTo(QPointF(-hw * 0.6, top - 26), QPointF(0, top - 26))
    hood.quadTo(QPointF(hw * 0.6, top - 26), QPointF(hw + 6, top + 26))
    hood.lineTo(QPointF(hw - 6, top + 26))
    hood.quadTo(QPointF(hw * 0.5, top - 8), QPointF(0, top - 8))
    hood.quadTo(QPointF(-hw * 0.5, top - 8), QPointF(-hw + 6, top + 26))
    hood.closeSubpath()
    _hat(b, hood, 'cloth')


def _sun_hat(b: Brush, t: Template, _kind: str) -> None:
    top, hw = _crown(t)
    _hat(b, ellipse(0, top, hw * 1.05, 15), 'cloth')
    dome = rounded(-hw * 0.66, top - 32, hw * 1.32, 34, 15)
    _hat(b, dome, 'cloth')
    _hat(b, rect(hw * 0.28, top - 22, 16, 13), 'trim', 3.5)


def _nightcap(b: Brush, t: Template, _kind: str) -> None:
    top, hw = _crown(t)
    cone = QPainterPath(QPointF(-hw * 0.7, top + 4))
    cone.quadTo(QPointF(-hw * 0.2, top - 46), QPointF(hw * 0.5, top - 30))
    cone.quadTo(QPointF(hw * 0.95, top - 20), QPointF(hw * 1.05, top + 18))
    cone.quadTo(QPointF(hw * 0.6, top - 4), QPointF(hw * 0.7, top + 4))
    cone.closeSubpath()
    _hat(b, cone, 'cloth')
    _hat(b, rounded(-hw * 0.74, top - 4, hw * 1.48, 14, 7), 'trim', 5)
    _hat(b, ellipse(hw * 1.05, top + 24, 10, 10), 'trim', 4.5)


def _witch_hat(b: Brush, t: Template, _kind: str) -> None:
    top, hw = _crown(t)
    _hat(b, ellipse(0, top - 2, hw * 1.05, 11), 'cloth')
    cone = polygon((-hw * 0.5, top - 4), (hw * 0.1, top - 58), (hw * 0.62, top - 54), (hw * 0.3, top - 40),
                   (hw * 0.5, top - 4))
    _hat(b, cone, 'cloth')
    b.clip(cone, lambda: b.fill(rect(-hw, top - 22, hw * 2, 12), 'trim'))


def _flat_cap(b: Brush, t: Template, _kind: str) -> None:
    top, hw = _crown(t)
    _hat(b, polygon((-hw * 0.62, top + 2), (-hw * 1.08, top + 8), (-hw * 0.62, top - 10)), 'trim', 4.5)
    _hat(b, rounded(-hw * 0.66, top - 32, hw * 1.32, 36, 12), 'cloth')
    b.fill(rect(-hw * 0.66, top - 8, hw * 1.32, 8), 'trim')


def _hard_hat(b: Brush, t: Template, _kind: str) -> None:
    top, hw = _crown(t)
    _hat(b, rounded(-hw * 0.9, top - 6, hw * 1.8, 12, 6), 'cloth')
    dome = QPainterPath(QPointF(-hw * 0.66, top))
    dome.quadTo(QPointF(-hw * 0.66, top - 36), QPointF(0, top - 36))
    dome.quadTo(QPointF(hw * 0.66, top - 36), QPointF(hw * 0.66, top))
    dome.closeSubpath()
    _hat(b, dome, 'cloth')
    b.outline(line((0, top - 34), (0, top - 2)), 5)


def _top_hat(b: Brush, t: Template, _kind: str) -> None:
    top, hw = _crown(t)
    _hat(b, rounded(-hw * 0.75, top - 8, hw * 1.5, 12, 6), 'cloth')
    tube = rect(-hw * 0.45, top - 46, hw * 0.9, 40)
    _hat(b, tube, 'cloth')
    b.clip(tube, lambda: b.fill(rect(-hw, top - 22, hw * 2, 12), 'trim'))
    b.outline(tube)


def _conductor_cap(b: Brush, t: Template, _kind: str) -> None:
    top, hw = _crown(t)
    _hat(b, rect(-hw * 0.62, top - 32, hw * 1.24, 34), 'cloth')
    _hat(b, polygon((-hw * 0.66, top), (hw * 0.66, top), (hw * 0.46, top + 12), (-hw * 0.46, top + 12)), 'trim')
    b.shape(ellipse(0, top - 16, 9, 9), 'badge', 3.5)


def _goggles(b: Brush, t: Template, _kind: str) -> None:
    top, hw = _crown(t)
    _hat(b, rounded(-hw * 0.95, top + 2, hw * 1.9, 9, 4), 'cloth', 4)
    for x in (-hw * 0.32, hw * 0.32):
        _hat(b, ellipse(x, top - 8, 17, 14), 'cloth')
        b.shape(ellipse(x, top - 8, 10, 8), 'lens', 3)


# --- neckwear -----------------------------------------------------------------
def _bow(b: Brush, t: Template, _kind: str) -> None:
    y = _chin(t) + 8
    for side in (-1, 1):
        b.shape(polygon((0, y), (side * 22, y - 11), (side * 22, y + 11)), 'cloth', 4.5)
    b.shape(rect(-6, y - 6, 12, 12), 'cloth', 4)


def _collar(b: Brush, t: Template, _kind: str) -> None:
    y = _chin(t) + 2
    b.shape(rounded(-40, y - 6, 80, 15, 7), 'cloth', 5)


def _scarf(b: Brush, t: Template, kind: str) -> None:
    y = _chin(t) + 2
    b.shape(rounded(-48, y - 8, 96, 20, 9), 'cloth', 5)
    if kind == 'lie':
        return  # the loose end lies tucked under a resting pet
    b.shape(polygon((14, y + 6), (36, y + 6), (39, y + 28), (17, y + 30)), 'cloth', 5)
    b.outline(line((20, y + 20), (36, y + 18)), 3.5)


# --- torso garments -------------------------------------------------------------
def _clipped(b: Brush, t: Template, kind: str, region: str, details) -> None:
    torso = t.torso(kind)
    b.clip(torso, lambda: (b.fill(rect(-120, -120, 240, 240), region), details()))
    b.outline(torso)


def _work_jacket(b: Brush, t: Template, kind: str) -> None:
    _clipped(b, t, kind, 'cloth', lambda: (b.shape(rect(-16, -12, 30, 26), 'pocket', 4),
                                         b.fill(rect(-120, 26, 240, 8), 'trim')))


def _poncho(b: Brush, t: Template, kind: str) -> None:
    if kind == 'lie':
        _clipped(b, t, kind, 'cloth', lambda: None)
        return
    top = t.torso(kind).boundingRect().top()
    cape = polygon((0, top - 12), (52, top + 58), (-52, top + 58))
    b.fill(cape, 'cloth')
    b.clip(cape, lambda: b.fill(rect(-80, top + 48, 160, 14), 'trim'))
    b.shape(rounded(-5, top - 4, 10, 52, 4), 'trim', 4)
    b.outline(cape)


def _apron(b: Brush, t: Template, kind: str) -> None:
    _clipped(b, t, kind, 'coatline', lambda: (b.fill(rect(-120, -6, 240, 120), 'cloth'),
                                             b.shape(rect(-14, 6, 28, 18), 'pocket', 4)))


def _club_jacket(b: Brush, t: Template, kind: str) -> None:
    _clipped(b, t, kind, 'cloth', lambda: (b.fill(rect(-120, 24, 240, 40), 'trim'),
                                         b.outline(line((0, -50), (0, 24)), 3.5),
                                         b.shape(rect(8, -10, 16, 10), 'trim', 3.5)))


def _overalls(b: Brush, t: Template, kind: str) -> None:
    _clipped(b, t, kind, 'cloth', lambda: (b.fill(rect(-120, -120, 240, 116), 'shirt'),
                                         b.fill(rect(-18, -26, 8, 30), 'cloth'),
                                         b.fill(rect(10, -26, 8, 30), 'cloth'),
                                         b.shape(rect(-12, 4, 24, 16), 'trim', 4)))


def _pajamas(b: Brush, t: Template, kind: str) -> None:
    def details() -> None:
        for dx, dy in ((0, -16), (-9, -7), (9, -7), (0, -7), (0, 2)):
            b.fill(rect(dx - 4, dy - 4, 8, 8), 'trim')
        b.fill(rect(-120, 30, 240, 10), 'cuff')
    _clipped(b, t, kind, 'cloth', details)


def _moon_cape(b: Brush, t: Template, kind: str) -> None:
    if kind == 'lie':
        _clipped(b, t, kind, 'cloth', lambda: None)
        return
    top = t.torso(kind).boundingRect().top()
    cape = QPainterPath(QPointF(-18, top - 4))
    cape.lineTo(QPointF(18, top - 4))
    cape.quadTo(QPointF(44, top + 40), QPointF(50, top + 62))
    cape.lineTo(QPointF(-50, top + 62))
    cape.quadTo(QPointF(-44, top + 40), QPointF(-18, top - 4))
    b.fill(cape, 'cloth')
    moon = ellipse(14, top + 34, 15, 15).subtracted(ellipse(21, top + 28, 13, 13))
    b.fill(moon, 'trim')
    b.outline(cape)


def _pit_suit(b: Brush, t: Template, kind: str) -> None:
    _clipped(b, t, kind, 'cloth', lambda: (b.fill(rect(-10, -120, 20, 240), 'panel'),
                                         b.shape(rect(-120, 8, 240, 10), 'belt', 4),
                                         b.shape(rect(-7, 7, 14, 12), 'belt', 3)))


def _vest(b: Brush, t: Template, kind: str) -> None:
    _clipped(b, t, kind, 'cloth', lambda: (b.fill(rect(-120, -120, 96, 240), 'trim'),
                                         b.fill(rect(24, -120, 96, 240), 'trim'),
                                         b.fill(rect(-120, 24, 240, 30), 'trim')))


def _work_overalls(b: Brush, t: Template, kind: str) -> None:
    _clipped(b, t, kind, 'cloth', lambda: b.shape(rect(-14, 2, 28, 20), 'pocket', 4))


def _trench(b: Brush, t: Template, kind: str) -> None:
    _clipped(b, t, kind, 'cloth', lambda: (b.fill(polygon((-30, -40), (0, -40), (-8, -6)), 'trim'),
                                         b.fill(polygon((30, -40), (0, -40), (8, -6)), 'trim'),
                                         b.fill(rect(-120, 12, 240, 8), 'trim')))


def _train_cape(b: Brush, t: Template, kind: str) -> None:
    _clipped(b, t, kind, 'cloth', lambda: b.fill(rect(-120, -120, 240, 100), 'trim')
             if kind == 'lie' else b.fill(polygon((-34, -40), (34, -40), (0, -12)), 'trim'))


def _wetsuit(b: Brush, t: Template, kind: str) -> None:
    _clipped(b, t, kind, 'cloth', lambda: b.shape(ellipse(0, 8, 18, 22), 'panel', 4))


def _sweater(b: Brush, t: Template, kind: str) -> None:
    _clipped(b, t, kind, 'cloth', lambda: (b.shape(rect(-16, 4, 32, 20), 'pocket', 4),
                                         b.fill(rect(-120, 32, 240, 8), 'pocket')))


# --- sleeves -------------------------------------------------------------------
def _sleeve(b: Brush, t: Template, _kind: str) -> None:
    """Covers the upper arm and follows its rotation; the paw stays visible."""
    b.shape(rounded(-12, -8, 24, 30, 10), 'sleeve', 5)


def _cuffed_sleeve(b: Brush, t: Template, _kind: str) -> None:
    sleeve = rounded(-12, -8, 24, 30, 10)
    b.fill(sleeve, 'sleeve')
    b.clip(sleeve, lambda: b.fill(rect(-14, 14, 28, 8), 'cuff'))
    b.outline(sleeve, 5)


def _sleeves(draw=_sleeve) -> tuple:
    return Piece('arm_l', 0, draw), Piece('arm_r', 0, draw)


# --- back and side items -----------------------------------------------------------
def _seed_bag(b: Brush, t: Template, kind: str) -> None:
    if kind == 'lie':
        return
    b.outline(line((-26, -30), (34, 12)), 5)
    bag = rounded(26, 6, 30, 28, 5)
    b.shape(bag, 'cloth')
    b.shape(polygon((26, 10), (56, 10), (50, 22), (32, 22)), 'trim', 4)


def _box_bag_back(b: Brush, t: Template, kind: str) -> None:
    if kind != 'lie':
        b.shape(rect(-46, -40, 92, 62), 'cloth')


def _straps(b: Brush, t: Template, kind: str) -> None:
    if kind == 'lie':
        return
    for x in (-18, 18):
        b.shape(rect(x - 5, -36, 10, 40), 'trim', 3.5)


def _gear_pack(b: Brush, t: Template, kind: str) -> None:
    if kind != 'lie':
        for x in (-30, 30):
            b.shape(rounded(x - 16, -42, 32, 64, 14), 'cloth')


C, P, K = ORANGE, PAPER, INK


def _g(ident, outfit, name, slots, palette, *pieces) -> Garment:
    return Garment(ident, outfit, name, tuple(slots), palette, tuple(pieces))


GARMENTS = (
    _g('work-cap', 'WORK', 'Work cap', ['head'], {'cloth': C}, Piece('head', HAT_Z, _work_cap)),
    _g('work-jacket', 'WORK', 'Work jacket', ['body'], {'cloth': K, 'pocket': P, 'trim': C, 'sleeve': K, 'cuff': C},
       Piece('body', BODY_Z, _work_jacket), *_sleeves(_cuffed_sleeve)),
    _g('rain-poncho', 'RAIN', 'Rain poncho', ['head', 'body'], {'cloth': C, 'trim': K},
       Piece('head', HAT_Z, _rain_hood), Piece('body', BODY_Z, _poncho)),
    _g('cafe-beret', 'NIGHT CAFE', 'Beret', ['head'], {'cloth': K, 'trim': C}, Piece('head', HAT_Z, _beret)),
    _g('bow-tie', 'NIGHT CAFE', 'Bow tie', ['neck'], {'cloth': C}, Piece('head', NECK_Z, _bow)),
    _g('cafe-apron', 'NIGHT CAFE', 'Apron', ['body'], {'coatline': C, 'cloth': P, 'pocket': K},
       Piece('body', BODY_Z, _apron)),
    _g('club-jacket', 'STREET CLUB', 'Club jacket', ['body'], {'cloth': K, 'trim': C, 'sleeve': P, 'cuff': C},
       Piece('body', BODY_Z, _club_jacket), *_sleeves(_cuffed_sleeve)),
    _g('sun-hat', 'SEED KEEPER', 'Sun hat', ['head'], {'cloth': P, 'trim': C}, Piece('head', HAT_Z, _sun_hat)),
    _g('overalls', 'SEED KEEPER', 'Overalls', ['body'], {'shirt': C, 'cloth': K, 'trim': C, 'sleeve': C},
       Piece('body', BODY_Z, _overalls), *_sleeves()),
    _g('seed-bag', 'SEED KEEPER', 'Seed bag', ['back'], {'cloth': P, 'trim': C}, Piece('body', STRAP_Z, _seed_bag)),
    _g('nightcap', 'OFF DUTY', 'Nightcap', ['head'], {'cloth': C, 'trim': P}, Piece('head', HAT_Z, _nightcap)),
    _g('pajamas', 'OFF DUTY', 'Pajamas', ['body'], {'cloth': K, 'trim': P, 'cuff': C, 'sleeve': K},
       Piece('body', BODY_Z, _pajamas), *_sleeves(_cuffed_sleeve)),
    _g('witch-hat', 'MOON WATCH', 'Pointed hat', ['head'], {'cloth': K, 'trim': C},
       Piece('head', HAT_Z, _witch_hat)),
    _g('collar', 'MOON WATCH', 'Collar', ['neck'], {'cloth': C}, Piece('head', NECK_Z, _collar)),
    _g('moon-cape', 'MOON WATCH', 'Moon cape', ['body'], {'cloth': P, 'trim': K}, Piece('body', BODY_Z, _moon_cape)),
    _g('pit-suit', 'PIT CREW', 'Pit suit', ['body'], {'cloth': C, 'panel': K, 'belt': P, 'sleeve': C},
       Piece('body', BODY_Z, _pit_suit), *_sleeves()),
    _g('express-cap', 'EXPRESS', 'Delivery cap', ['head'], {'cloth': P, 'trim': K}, Piece('head', HAT_Z, _flat_cap)),
    _g('express-vest', 'EXPRESS', 'Vest', ['body'], {'cloth': P, 'trim': K}, Piece('body', BODY_Z, _vest)),
    _g('box-bag', 'EXPRESS', 'Box bag', ['back'], {'cloth': K, 'trim': C},
       Piece('body', BACK_Z, _box_bag_back), Piece('body', STRAP_Z, _straps)),
    _g('hard-hat', 'FIX IT', 'Hard hat', ['head'], {'cloth': C}, Piece('head', HAT_Z, _hard_hat)),
    _g('work-overalls', 'FIX IT', 'Work overalls', ['body'], {'cloth': P, 'pocket': K, 'sleeve': P},
       Piece('body', BODY_Z, _work_overalls), *_sleeves()),
    _g('top-hat', 'NIGHT SHIFT', 'Top hat', ['head'], {'cloth': K, 'trim': C}, Piece('head', HAT_Z, _top_hat)),
    _g('trench', 'NIGHT SHIFT', 'Short trench', ['body'], {'cloth': P, 'trim': K, 'sleeve': P}, Piece('body', BODY_Z, _trench), *_sleeves()),
    _g('conductor-cap', 'LAST TRAIN', 'Conductor cap', ['head'], {'cloth': C, 'trim': K, 'badge': P},
       Piece('head', HAT_Z, _conductor_cap)),
    _g('train-cape', 'LAST TRAIN', 'Short cape', ['body'], {'cloth': K, 'trim': P},
       Piece('body', BODY_Z, _train_cape)),
    _g('goggles', 'DEEP DIVE', 'Goggles', ['head'], {'cloth': K, 'lens': C}, Piece('head', HAT_Z, _goggles)),
    _g('wetsuit', 'DEEP DIVE', 'Wetsuit', ['body'], {'cloth': C, 'panel': K, 'sleeve': C}, Piece('body', BODY_Z, _wetsuit), *_sleeves()),
    _g('gear-pack', 'DEEP DIVE', 'Gear pack', ['back'], {'cloth': C, 'trim': K},
       Piece('body', BACK_Z, _gear_pack), Piece('body', STRAP_Z, _straps)),
    _g('big-scarf', 'SLOW SUNDAY', 'Big scarf', ['neck'], {'cloth': C}, Piece('head', NECK_Z, _scarf)),
    _g('sweater', 'SLOW SUNDAY', 'Wide sweater', ['body'], {'cloth': K, 'pocket': P, 'sleeve': K, 'cuff': P},
       Piece('body', BODY_Z, _sweater), *_sleeves(_cuffed_sleeve)),
)

# The authored combinations and the body type each was designed on first. Every
# piece is still built for every body type, so any pet can mix them freely.
OUTFITS = (
    ('WORK', 'inkside-mochi', ('work-cap', 'work-jacket')),
    ('RAIN', 'inkside-mochi', ('rain-poncho',)),
    ('NIGHT CAFE', 'inkside-mochi', ('cafe-beret', 'bow-tie', 'cafe-apron')),
    ('STREET CLUB', 'inkside-mochi', ('club-jacket',)),
    ('SEED KEEPER', 'inkside-moss', ('sun-hat', 'overalls', 'seed-bag')),
    ('OFF DUTY', 'inkside-moss', ('nightcap', 'pajamas')),
    ('MOON WATCH', 'inkside-pip', ('witch-hat', 'collar', 'moon-cape')),
    ('PIT CREW', 'inkside-pip', ('pit-suit',)),
    ('EXPRESS', 'inkside-bolt', ('express-cap', 'express-vest', 'box-bag')),
    ('FIX IT', 'inkside-bolt', ('hard-hat', 'work-overalls')),
    ('NIGHT SHIFT', 'inkside-ink', ('top-hat', 'trench')),
    ('LAST TRAIN', 'inkside-ink', ('conductor-cap', 'bow-tie', 'train-cape')),
    ('DEEP DIVE', 'inkside-gill', ('goggles', 'wetsuit', 'gear-pack')),
    ('SLOW SUNDAY', 'inkside-gill', ('big-scarf', 'sweater')),
)
