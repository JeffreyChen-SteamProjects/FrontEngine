"""The INKSIDE wardrobe: nineteen outfits split into wearable slot pieces.

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

_WINTER_WALK = 'WINTER WALK'
_SCHOOL_DAY = 'SCHOOL DAY'
_BEACH_DAY = 'BEACH DAY'


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


# --- the second wardrobe: winter, kitchen, party, school and beach -------------------
def _knit_beanie(b: Brush, t: Template, _kind: str) -> None:
    top, hw = _crown(t)
    dome = QPainterPath(QPointF(-hw * 0.68, top + 2))
    dome.quadTo(QPointF(-hw * 0.7, top - 40), QPointF(0, top - 40))
    dome.quadTo(QPointF(hw * 0.7, top - 40), QPointF(hw * 0.68, top + 2))
    dome.closeSubpath()
    _hat(b, dome, 'cloth')
    b.clip(dome, lambda: [b.outline(line((x, top - 32), (x, top - 6)), 3) for x in (-hw * 0.3, 0, hw * 0.3)])
    _hat(b, rounded(-hw * 0.74, top - 8, hw * 1.48, 14, 6), 'trim', 5)
    _hat(b, ellipse(0, top - 44, 10, 10), 'trim', 4.5)


def _chef_hat(b: Brush, t: Template, _kind: str) -> None:
    top, hw = _crown(t)
    puff = ellipse(-hw * 0.3, top - 32, hw * 0.34, 17).united(ellipse(hw * 0.3, top - 32, hw * 0.34, 17))
    puff = puff.united(ellipse(0, top - 40, hw * 0.4, 19))
    _hat(b, puff, 'cloth')
    _hat(b, rect(-hw * 0.5, top - 20, hw, 20), 'cloth')
    b.outline(line((-hw * 0.5, top - 20), (hw * 0.5, top - 20)), 3.5)


def _party_hat(b: Brush, t: Template, _kind: str) -> None:
    top, hw = _crown(t)
    cone = polygon((-hw * 0.42, top + 2), (hw * 0.06, top - 50), (hw * 0.46, top + 2))
    _hat(b, cone, 'cloth')
    b.clip(cone, lambda: [b.fill(polygon((-hw, top - y), (hw, top - y - 14), (hw, top - y - 6), (-hw, top - y + 8)),
                                 'trim') for y in (6, 24, 42)])
    b.outline(cone)
    _hat(b, ellipse(hw * 0.06, top - 52, 9, 9), 'trim', 4)


def _student_cap(b: Brush, t: Template, _kind: str) -> None:
    top, hw = _crown(t)
    _hat(b, ellipse(hw * 0.46, top + 2, hw * 0.52, 8), 'trim', 4.5)
    _hat(b, rounded(-hw * 0.62, top - 28, hw * 1.24, 32, 14), 'cloth')
    b.shape(ellipse(0, top - 28, 6, 5), 'trim', 3)


def _straw_hat(b: Brush, t: Template, _kind: str) -> None:
    top, hw = _crown(t)
    brim = ellipse(0, top - 2, hw * 1.3, 15)
    _hat(b, brim, 'cloth')
    crown = rounded(-hw * 0.56, top - 28, hw * 1.12, 28, 12)
    _hat(b, crown, 'cloth')
    b.clip(crown, lambda: b.fill(rect(-hw, top - 12, hw * 2, 9), 'trim'))
    b.outline(crown)
    b.outline(line((-hw * 1.0, top + 2), (-hw * 0.7, top + 4)), 2.5)
    b.outline(line((hw * 0.7, top + 4), (hw * 1.0, top + 2)), 2.5)


def _neckerchief(b: Brush, t: Template, _kind: str) -> None:
    y = _chin(t) + 4
    b.shape(polygon((-26, y - 6), (26, y - 6), (0, y + 24)), 'cloth', 5)
    b.shape(ellipse(0, y - 4, 8, 7), 'trim', 4)


def _flower_lei(b: Brush, t: Template, _kind: str) -> None:
    y = _chin(t) + 6
    for index, x in enumerate((-36, -24, -12, 0, 12, 24, 36)):
        dip = 8 - abs(x) / 6
        b.shape(ellipse(x, y + dip, 8, 8), 'cloth' if index % 2 else 'trim', 3.5)


def _puffer(b: Brush, t: Template, kind: str) -> None:
    _clipped(b, t, kind, 'cloth', lambda: ([b.outline(line((-120, y), (120, y)), 3.5) for y in (-26, -8, 10, 28)],
                                         b.fill(rect(-3, -120, 6, 240), 'trim')))


def _chef_jacket(b: Brush, t: Template, kind: str) -> None:
    def details() -> None:
        for x in (-10, 10):
            for y in (-20, -4, 12):
                b.fill(ellipse(x, y, 3.5, 3.5), 'trim')
    _clipped(b, t, kind, 'cloth', details)


def _confetti_shirt(b: Brush, t: Template, kind: str) -> None:
    def details() -> None:
        spots = ((-30, -30), (12, -36), (-8, -14), (28, -10), (-26, 8), (6, 14), (30, 26), (-12, 30))
        for index, (x, y) in enumerate(spots):
            b.fill(rect(x - 4, y - 4, 8, 8) if index % 2 else ellipse(x, y, 4.5, 4.5),
                   'trim' if index % 3 else 'pocket')
    _clipped(b, t, kind, 'cloth', details)


def _blazer(b: Brush, t: Template, kind: str) -> None:
    _clipped(b, t, kind, 'cloth', lambda: (b.fill(polygon((-28, -44), (0, -44), (-6, 0)), 'trim'),
                                         b.fill(polygon((28, -44), (0, -44), (6, 0)), 'trim'),
                                         b.outline(line((0, 0), (0, 40)), 3),
                                         b.shape(rect(-30, -8, 12, 7), 'pocket', 3)))


def _striped_tee(b: Brush, t: Template, kind: str) -> None:
    _clipped(b, t, kind, 'cloth', lambda: [b.fill(rect(-120, y, 240, 7), 'trim') for y in (-30, -14, 2, 18, 34)])


def _satchel(b: Brush, t: Template, kind: str) -> None:
    if kind == 'lie':
        return
    b.outline(line((26, -30), (-34, 12)), 5)
    bag = rounded(-58, 4, 34, 30, 5)
    b.shape(bag, 'cloth')
    b.shape(polygon((-58, 4), (-24, 4), (-28, 18), (-54, 18)), 'trim', 4)
    b.fill(rect(-44, 15, 6, 6), 'cloth')


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
    _g('knit-beanie', _WINTER_WALK, 'Knit beanie', ['head'], {'cloth': C, 'trim': P}, Piece('head', HAT_Z, _knit_beanie)),
    _g('puffer-jacket', _WINTER_WALK, 'Puffer jacket', ['body'], {'cloth': C, 'trim': K, 'sleeve': C, 'cuff': K},
       Piece('body', BODY_Z, _puffer), *_sleeves(_cuffed_sleeve)),
    _g('chef-hat', 'KITCHEN', 'Chef hat', ['head'], {'cloth': P}, Piece('head', HAT_Z, _chef_hat)),
    _g('neckerchief', 'KITCHEN', 'Neckerchief', ['neck'], {'cloth': C, 'trim': K}, Piece('head', NECK_Z, _neckerchief)),
    _g('chef-jacket', 'KITCHEN', 'Chef jacket', ['body'], {'cloth': P, 'trim': K, 'sleeve': P, 'cuff': K},
       Piece('body', BODY_Z, _chef_jacket), *_sleeves(_cuffed_sleeve)),
    _g('party-hat', 'PARTY', 'Party hat', ['head'], {'cloth': C, 'trim': P}, Piece('head', HAT_Z, _party_hat)),
    _g('confetti-shirt', 'PARTY', 'Confetti shirt', ['body'], {'cloth': K, 'trim': C, 'pocket': P, 'sleeve': K},
       Piece('body', BODY_Z, _confetti_shirt), *_sleeves()),
    _g('student-cap', _SCHOOL_DAY, 'Student cap', ['head'], {'cloth': K, 'trim': C}, Piece('head', HAT_Z, _student_cap)),
    _g('blazer', _SCHOOL_DAY, 'Blazer', ['body'], {'cloth': K, 'trim': P, 'pocket': C, 'sleeve': K, 'cuff': P},
       Piece('body', BODY_Z, _blazer), *_sleeves(_cuffed_sleeve)),
    _g('satchel', _SCHOOL_DAY, 'Satchel', ['back'], {'cloth': C, 'trim': K}, Piece('body', STRAP_Z, _satchel)),
    _g('straw-hat', _BEACH_DAY, 'Straw hat', ['head'], {'cloth': P, 'trim': C}, Piece('head', HAT_Z, _straw_hat)),
    _g('flower-lei', _BEACH_DAY, 'Flower lei', ['neck'], {'cloth': C, 'trim': P}, Piece('head', NECK_Z, _flower_lei)),
    _g('striped-tee', _BEACH_DAY, 'Striped tee', ['body'], {'cloth': P, 'trim': C, 'sleeve': P},
       Piece('body', BODY_Z, _striped_tee), *_sleeves()),
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
    (_WINTER_WALK, 'inkside-mochi', ('knit-beanie', 'puffer-jacket', 'big-scarf')),
    ('KITCHEN', 'inkside-moss', ('chef-hat', 'neckerchief', 'chef-jacket')),
    ('PARTY', 'inkside-pip', ('party-hat', 'bow-tie', 'confetti-shirt')),
    (_SCHOOL_DAY, 'inkside-bolt', ('student-cap', 'blazer', 'satchel')),
    (_BEACH_DAY, 'inkside-gill', ('straw-hat', 'flower-lei', 'striped-tee')),
)
