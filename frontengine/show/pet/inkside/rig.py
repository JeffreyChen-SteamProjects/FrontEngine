"""Template-independent poses and the action timelines built from them.

Every character uses the same parts placed at template-specific base points.
A pose moves those parts (and their rotations) relative to the base, so one
timeline animates all six body types and every garment follows the same frames.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

PARTS = ('head', 'neck', 'body', 'tail', 'arm_l', 'arm_r', 'foot_l', 'foot_r')


@dataclass(frozen=True)
class Pose:
    duration: int
    root: tuple[int, int] = (0, 0)
    moves: dict = field(default_factory=dict)
    turns: dict = field(default_factory=dict)
    torso: str = 'stand'
    eyes: str = 'open'
    mouth: str = 'rest'
    fx: tuple = ()
    front: tuple = ()        # arms drawn in front of the head (paws at the mouth)
    gaze: tuple = (0, 0)     # eyes and mouth shift toward where the pet is heading

    def offset(self, part: str) -> tuple[int, int]:
        dx, dy = self.moves.get(part, (0, 0))
        if part in ('arm_l', 'arm_r') and part not in self.front and abs(self.angle(part)) >= 90:
            # A raised arm swings out from a lower, wider shoulder so the paw clears the head.
            dx += -14 if part == 'arm_l' else 14
            dy += 6
        return dx + self.root[0], dy + self.root[1]

    def angle(self, part: str) -> int:
        return self.turns.get(part, 0)


def pose(duration: int, **values) -> Pose:
    return Pose(duration, **values)


ARMS_UP = {'arm_l': 115, 'arm_r': -115}
ARMS_HIGH = {'arm_l': 128, 'arm_r': -128}
SIT = {'head': (0, 10), 'neck': (0, 10), 'arm_l': (2, 12), 'arm_r': (-2, 12),
       'foot_l': (-8, 0), 'foot_r': (8, 0), 'tail': (0, 8)}
LIE = {'head': (-16, 44), 'neck': (-16, 44), 'arm_l': (-30, 44), 'arm_r': (-4, 46),
       'foot_l': (24, 0), 'foot_r': (38, 0), 'tail': (14, 10)}


def _idle() -> tuple[bool, list[Pose]]:
    return True, [pose(700), pose(500, root=(0, 2)), pose(700), pose(140, eyes='closed')]


def _walk() -> tuple[bool, list[Pose]]:
    """Six-step gait sized to read at desktop-pet size.

    Each foot strides 22 px forward and back and lifts 16 px while the other plants;
    the body bounces on every step, the head waddles side to side, arms swing against
    the legs and the face looks ahead. One cycle (two steps) lasts 450 ms, so the feet
    keep pace with the default walking speed instead of skating.
    """
    frames = []
    for step in range(6):
        phase = 2 * math.pi * step / 6
        lead = round(22 * math.cos(phase))
        lift_l = round(-16 * max(0.0, math.sin(phase)))
        lift_r = round(-16 * max(0.0, -math.sin(phase)))
        bounce = round(-7 * abs(math.sin(phase)))
        swing = round(40 * math.cos(phase))
        waddle = round(5 * math.sin(phase))
        frames.append(pose(75, root=(0, bounce), gaze=(10, 0),
                           moves={'foot_l': (lead, lift_l), 'foot_r': (-lead, lift_r), 'head': (3 + waddle // 2, 2)},
                           turns={'arm_l': -swing, 'arm_r': -swing, 'head': waddle,
                                  'tail': round(16 * math.sin(phase))}))
    return True, frames


def _sleep() -> tuple[bool, list[Pose]]:
    lying = dict(torso='lie', moves=LIE, turns={'head': -8, 'tail': -20, 'arm_l': 80, 'arm_r': 80},
                 eyes='closed')
    return True, [pose(900, fx=('zzz_small',), **lying),
                  pose(900, root=(0, 1), fx=('zzz',), **lying)]


def _sit() -> tuple[bool, list[Pose]]:
    sitting = dict(torso='sit', moves=SIT)
    return True, [pose(900, **sitting), pose(600, root=(0, 1), **sitting),
                  pose(140, eyes='closed', **sitting)]


def _climb() -> tuple[bool, list[Pose]]:
    """Hand over hand: one paw reaches high while the other pulls, the opposite foot pushes
    and the body hitches upward, face turned up toward the wall."""
    reach, pull = 172, 118
    frames = []
    for left_high in (True, False):
        high, low = ('arm_l', 'arm_r') if left_high else ('arm_r', 'arm_l')
        sign = {'arm_l': 1, 'arm_r': -1}
        push = 'foot_r' if left_high else 'foot_l'
        rest = 'foot_l' if left_high else 'foot_r'
        turns = {high: sign[high] * reach, low: sign[low] * pull, 'head': -6, 'tail': 18 if left_high else -18}
        moves = {high: (0, -16), low: (0, -4), push: (0, -14), rest: (0, 2)}
        frames.append(pose(170, root=(0, 2), moves=moves, turns=turns, gaze=(8, -6), front=(high,)))
        frames.append(pose(150, root=(0, -6), moves={**moves, push: (0, -4)}, turns=turns, gaze=(8, -6),
                           front=(high,)))
    return True, frames


def _fall() -> tuple[bool, list[Pose]]:
    spread = {'foot_l': (-6, -6), 'foot_r': (6, -6), 'tail': (0, -4)}
    return True, [pose(160, moves=spread, turns={'arm_l': 108, 'arm_r': -108, 'tail': -25}, mouth='open'),
                  pose(160, root=(0, -2), moves=spread, turns={'arm_l': 122, 'arm_r': -122, 'tail': -15},
                       mouth='open')]


def _drag() -> tuple[bool, list[Pose]]:
    dangle = {'foot_l': (2, 6), 'foot_r': (-2, 6), 'arm_l': (0, -6), 'arm_r': (0, -6)}
    return True, [pose(320, root=(-3, -8), moves=dangle, turns={**ARMS_UP, 'tail': 15}),
                  pose(320, root=(3, -8), moves=dangle, turns={**ARMS_HIGH, 'tail': 22})]


def _greet() -> tuple[bool, list[Pose]]:
    return True, [pose(180, turns={'arm_r': -108}, eyes='happy'),
                  pose(180, turns={'arm_r': -132}, eyes='happy'),
                  pose(180, turns={'arm_r': -108}),
                  pose(180, turns={'arm_r': -132})]


def _pet() -> tuple[bool, list[Pose]]:
    frames = []
    for index, (tilt, wag) in enumerate(((6, 10), (8, -12), (6, 10), (4, -12))):
        frames.append(pose(260, root=(0, 2), turns={'head': tilt, 'tail': wag}, eyes='happy',
                           fx=(f'heart_{index}',)))
    return True, frames


def _feed() -> tuple[bool, list[Pose]]:
    hold = {'arm_l': 150, 'arm_r': -150}
    lift = {'arm_l': (14, -4), 'arm_r': (-14, -4)}
    paws = ('arm_l', 'arm_r')
    return True, [pose(200, moves=lift, turns=hold, mouth='open', front=paws),
                  pose(200, root=(0, 2), moves=lift, turns=hold, front=paws),
                  pose(200, moves=lift, turns=hold, mouth='open', front=paws),
                  pose(200, root=(0, 2), moves=lift, turns=hold, eyes='happy', front=paws)]


def _groom() -> tuple[bool, list[Pose]]:
    """Three rubbing passes, then a stretch held until the 3-second groom completes."""
    rub = [(-14, -14), (-8, -20), (-14, -14), (-8, -20)]
    frames = [pose(220, moves={'arm_r': rub[index % 4]}, turns={'arm_r': -160, 'head': 4 - 8 * (index % 2)},
                   eyes='closed', front=('arm_r',)) for index in range(12)]
    return False, frames + [pose(360, root=(0, -2), turns=ARMS_HIGH, eyes='happy', mouth='open')]


def _play() -> tuple[bool, list[Pose]]:
    return True, [
        pose(200, root=(0, 4), turns={'arm_l': 50, 'arm_r': -50, 'tail': 12}),
        pose(160, root=(0, -10), turns={'arm_l': 120, 'arm_r': -120, 'tail': -12}, mouth='open'),
        pose(140, root=(0, -5), turns={'arm_l': 90, 'arm_r': -90}),
        pose(180, turns={'tail': 15}, eyes='happy'),
    ]


def _celebrate() -> tuple[bool, list[Pose]]:
    return True, [pose(170, root=(0, 4), turns={'arm_l': 60, 'arm_r': -60}),
                  pose(170, root=(0, -8), turns=ARMS_UP, eyes='happy', mouth='open', fx=('sparkle',)),
                  pose(170, root=(0, -4), turns=ARMS_HIGH, eyes='happy', mouth='open',
                       fx=('sparkle_big',)),
                  pose(170, eyes='happy')]


def _outfit_show() -> tuple[bool, list[Pose]]:
    return True, [pose(220, root=(-4, 0), turns={'arm_r': -120}, eyes='happy'),
                  pose(220, root=(0, -6), turns=ARMS_UP, eyes='happy', fx=('sparkle',)),
                  pose(220, root=(4, 0), turns={'arm_l': 120}, eyes='happy'),
                  pose(220)]


def _wake() -> tuple[bool, list[Pose]]:
    return False, [pose(500, torso='lie', moves=LIE, turns={'head': -8, 'tail': -20, 'arm_l': 80, 'arm_r': 80},
                        eyes='closed'),
                   pose(400, torso='sit', moves=SIT, eyes='closed', mouth='open'),
                   pose(500, turns=ARMS_UP, eyes='happy')]


def _sleep_in() -> tuple[bool, list[Pose]]:
    return False, [pose(500, turns={'arm_r': -160}, moves={'arm_r': (-12, -12)}, eyes='closed', mouth='open',
                        front=('arm_r',)),
                   pose(400, torso='sit', moves=SIT, eyes='closed'),
                   pose(600, torso='lie', moves=LIE, turns={'head': -8, 'tail': -20, 'arm_l': 80, 'arm_r': 80},
                        eyes='closed', fx=('zzz_small',))]


def _land() -> tuple[bool, list[Pose]]:
    return False, [pose(120, root=(0, 6), moves={'foot_l': (-6, -6), 'foot_r': (6, -6)},
                        turns={'arm_l': 70, 'arm_r': -70}, eyes='squint'),
                   pose(160, root=(0, -2))]


def _food_like() -> tuple[bool, list[Pose]]:
    return True, [pose(220, eyes='happy', mouth='open', fx=('heart_0',)),
                  pose(220, root=(0, -6), turns={'arm_l': 60, 'arm_r': -60}, eyes='happy', fx=('heart_1',)),
                  pose(220, eyes='happy', mouth='open', fx=('heart_2',))]


def _food_dislike() -> tuple[bool, list[Pose]]:
    return True, [pose(160, moves={'head': (-5, 0)}, turns={'head': -6}, eyes='squint', fx=('sweat',)),
                  pose(160, moves={'head': (5, 0)}, turns={'head': 6}, eyes='squint', fx=('sweat',)),
                  pose(160, moves={'head': (-5, 0)}, turns={'head': -6}, eyes='squint'),
                  pose(200, eyes='squint')]


def _peer_greet() -> tuple[bool, list[Pose]]:
    return True, [pose(200, turns={'arm_l': 118}, eyes='happy', fx=('note',)),
                  pose(200, root=(0, -4), turns={'arm_l': 130, 'arm_r': -110}, eyes='happy', mouth='open'),
                  pose(200, turns={'arm_r': -128}, eyes='happy'),
                  pose(200)]


def _catch() -> tuple[bool, list[Pose]]:
    return True, [pose(180, root=(0, -8), turns=ARMS_UP, mouth='open', fx=('ball_high',)),
                  pose(180, root=(0, -4), turns=ARMS_HIGH, fx=('ball_hold',)),
                  pose(220, turns=ARMS_UP, eyes='happy', fx=('ball_hold',))]


# --- home poses: what a pet does at a piece of furniture, with its props drawn as layers --------
SITTING = dict(torso='sit', moves=SIT)
HOLD_FRONT = {'arm_l': 96, 'arm_r': -96}


def _write() -> tuple[bool, list[Pose]]:
    """Sitting at a desk: the right paw moves a pencil across a sheet, a short pause to think."""
    down = {'head': 4}
    return True, [
        pose(320, turns={**down, 'arm_r': -78}, gaze=(6, 6), fx=('paper', 'pencil_0'), front=('arm_r',), **SITTING),
        pose(320, turns={**down, 'arm_r': -88}, gaze=(8, 6), fx=('paper', 'pencil_1'), front=('arm_r',), **SITTING),
        pose(320, turns={**down, 'arm_r': -78}, gaze=(6, 6), fx=('paper', 'pencil_0'), front=('arm_r',), **SITTING),
        pose(420, root=(0, 1), turns={'head': -4, 'arm_r': -70}, eyes='closed', fx=('paper', 'pencil_0'),
             front=('arm_r',), **SITTING),
    ]


def _garden() -> tuple[bool, list[Pose]]:
    """Standing by a plant: the watering can tilts forward, drops fall, the can tilts back."""
    hold = {'arm_r': -96}
    return True, [pose(300, turns=hold, gaze=(8, 4), fx=('can_0',)),
                  pose(300, turns={'arm_r': -84, 'head': 4}, gaze=(10, 6), fx=('can_1', 'drops')),
                  pose(300, root=(0, 1), turns={'arm_r': -84, 'head': 4}, gaze=(10, 6), fx=('can_1', 'drops_low')),
                  pose(300, turns=hold, gaze=(8, 4), eyes='happy', fx=('can_0',))]


def _craft() -> tuple[bool, list[Pose]]:
    """At a workbench: mallet raised, coming down, impact on the block, recovering."""
    return True, [pose(200, turns={'arm_r': -150}, gaze=(8, 4), fx=('block', 'mallet_up')),
                  pose(140, turns={'arm_r': -110}, gaze=(8, 6), fx=('block', 'mallet_mid')),
                  pose(160, root=(0, 2), turns={'arm_r': -74, 'head': 3}, eyes='squint', gaze=(8, 6),
                       fx=('block', 'mallet_down', 'spark_small')),
                  pose(200, turns={'arm_r': -96}, gaze=(8, 4), fx=('block', 'mallet_mid'))]


def _read() -> tuple[bool, list[Pose]]:
    """Sitting with an open book held in both paws: reading along, a page turns, a small nod."""
    paws = ('arm_l', 'arm_r')
    return True, [pose(480, turns={**HOLD_FRONT, 'head': 3}, gaze=(2, 6), fx=('book',), front=paws, **SITTING),
                  pose(480, root=(0, 1), turns={**HOLD_FRONT, 'head': 5}, gaze=(6, 6), fx=('book',), front=paws,
                       **SITTING),
                  pose(360, turns={'arm_l': 96, 'arm_r': -120, 'head': 3}, gaze=(4, 6), fx=('book_turn',),
                       front=paws, **SITTING),
                  pose(480, turns={**HOLD_FRONT, 'head': 3}, eyes='closed', fx=('book',), front=paws, **SITTING)]


def _music() -> tuple[bool, list[Pose]]:
    """Sitting at a keyboard: the paws press in turn, the head bobs to the beat."""
    return True, [pose(220, root=(0, 1), turns={'arm_l': 70, 'arm_r': -96, 'head': -4}, gaze=(4, 4),
                       fx=('keys',), **SITTING),
                  pose(220, turns={'arm_l': 96, 'arm_r': -70, 'head': 4}, gaze=(4, 4), eyes='happy',
                       fx=('keys', 'note'), **SITTING),
                  pose(220, root=(0, 1), turns={'arm_l': 70, 'arm_r': -96, 'head': -4}, gaze=(4, 4),
                       fx=('keys',), **SITTING),
                  pose(220, turns={'arm_l': 96, 'arm_r': -70, 'head': 4}, gaze=(4, 4), mouth='open',
                       fx=('keys', 'note'), **SITTING)]


def _paint() -> tuple[bool, list[Pose]]:
    """Standing at an easel: the brush reaches out for a stroke, pulls back, the head tilts to look."""
    return True, [pose(320, turns={'arm_r': -112}, gaze=(8, 0), fx=('brush_0',)),
                  pose(320, turns={'arm_r': -128}, gaze=(10, -2), fx=('brush_1',)),
                  pose(320, turns={'arm_r': -96, 'head': -6}, gaze=(6, 0), fx=('brush_2',)),
                  pose(320, turns={'arm_r': -112, 'head': -6}, eyes='happy', gaze=(8, 0), fx=('brush_0',))]


def _watch() -> tuple[bool, list[Pose]]:
    """Sitting and watching something off to the side: leaning in, a slow blink, a head tilt."""
    return True, [pose(520, turns={'head': 4, 'tail': 10}, gaze=(12, -2), **SITTING),
                  pose(520, root=(0, 1), turns={'head': 6, 'tail': -10}, gaze=(14, -2), **SITTING),
                  pose(200, turns={'head': 6, 'tail': 10}, gaze=(14, -2), eyes='closed', **SITTING),
                  pose(520, turns={'head': 10, 'tail': -10}, gaze=(12, -4), **SITTING)]


def _bathe() -> tuple[bool, list[Pose]]:
    """Sitting in the bath: both paws rub the head, soap bubbles float up and pop."""
    paws = ('arm_l', 'arm_r')
    scrub = {'arm_l': (12, -14), 'arm_r': (-12, -14)}
    return True, [pose(360, moves={**SIT, **scrub}, turns={'arm_l': 160, 'arm_r': -160}, eyes='happy',
                       fx=('bubbles_0',), front=paws, torso='sit'),
                  pose(360, root=(0, 1), moves={**SIT, **scrub}, turns={'arm_l': 150, 'arm_r': -168, 'head': 4},
                       eyes='closed', fx=('bubbles_1',), front=paws, torso='sit'),
                  pose(360, moves={**SIT, **scrub}, turns={'arm_l': 168, 'arm_r': -150, 'head': -4},
                       eyes='happy', fx=('bubbles_0',), front=paws, torso='sit'),
                  pose(360, root=(0, 1), moves={**SIT, **scrub}, turns={'arm_l': 160, 'arm_r': -160},
                       eyes='closed', mouth='open', fx=('bubbles_1',), front=paws, torso='sit')]


def _dress() -> tuple[bool, list[Pose]]:
    """Admiring itself in the wardrobe mirror: a turn to one side, smoothing its chest, a proud pose."""
    return True, [pose(300, root=(-3, 0), turns={'arm_r': -150, 'head': -6}, moves={'arm_r': (-10, -6)},
                       front=('arm_r',), eyes='happy'),
                  pose(300, root=(3, 0), turns={'arm_l': 150, 'head': 6}, moves={'arm_l': (10, -6)},
                       front=('arm_l',), eyes='happy'),
                  pose(300, root=(0, -6), turns=ARMS_UP, eyes='happy', mouth='open', fx=('sparkle',)),
                  pose(300, turns={'arm_l': 40, 'arm_r': -40}, eyes='happy')]


TIMELINES = {
    'idle': _idle, 'walk': _walk, 'sleep': _sleep, 'sit': _sit, 'climb': _climb, 'fall': _fall,
    'drag': _drag, 'land': _land, 'greet': _greet, 'pet': _pet, 'feed': _feed, 'groom': _groom,
    'play': _play, 'celebrate': _celebrate, 'outfit_show': _outfit_show, 'wake': _wake,
    'sleep_in': _sleep_in, 'food_like': _food_like, 'food_dislike': _food_dislike,
    'peer_greet': _peer_greet, 'catch': _catch,
    'write': _write, 'garden': _garden, 'craft': _craft, 'read': _read, 'music': _music,
    'paint': _paint, 'watch': _watch, 'bathe': _bathe, 'dress': _dress,
}


def timelines() -> dict[str, tuple[bool, list[Pose]]]:
    """Fresh copies so callers can adjust poses for one template safely."""
    return {name: (loop, [replace(frame) for frame in frames])
            for name, (loop, frames) in ((name, build()) for name, build in TIMELINES.items())}
