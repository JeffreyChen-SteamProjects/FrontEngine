"""
打字時寵物安分下來。

時鐘是注入的，所以測試不必真的等兩秒。這裡要釘住兩件事：安分時**每一種行為**都
不能移動（漏掉一種，那一種就是打字時還在跑的那隻），以及停手之後一定會恢復——
永遠停住的寵物看起來就是壞了。

The pet settles while you type.

The clock is injected, so nothing waits two seconds. Two things are pinned: while
settled *every* behaviour stays put - miss one and that is the pet still running
about while you type - and it always recovers afterwards, because a pet frozen
for good simply looks broken.
"""
import pytest

from frontengine.show.pet.desktop_pet import (
    BEHAVIOUR_CHASE, BEHAVIOUR_FLOOR, BEHAVIOUR_WANDER, PetMotion,
)
from frontengine.utils.input_watch.typing_watch import (
    DEFAULT_SETTLE_SECONDS, MAX_SETTLE_SECONDS, MIN_SETTLE_SECONDS, TypingWatch,
    clamp_settle_seconds,
)


class FakeClock:
    def __init__(self, now=1000.0):
        self.now = now

    def __call__(self):
        return self.now


def test_nothing_typed_yet_is_not_typing():
    watch = TypingWatch(clock=FakeClock())
    assert watch.typing() is False
    assert watch.seconds_since_key() is None


def test_a_keypress_counts_as_typing():
    clock = FakeClock()
    watch = TypingWatch(settle_seconds=2.0, clock=clock)
    watch.note_key()
    assert watch.typing() is True


def test_typing_stops_once_the_window_passes():
    clock = FakeClock()
    watch = TypingWatch(settle_seconds=2.0, clock=clock)
    watch.note_key()

    clock.now += 1.9
    assert watch.typing() is True
    clock.now += 0.2
    assert watch.typing() is False


def test_each_keypress_extends_the_window():
    """連續打字時不能每兩秒放行一次——寵物會一直抽動。"""
    clock = FakeClock()
    watch = TypingWatch(settle_seconds=2.0, clock=clock)
    watch.note_key()
    for _ in range(5):
        clock.now += 1.5
        watch.note_key()
        assert watch.typing() is True


def test_clearing_releases_immediately():
    clock = FakeClock()
    watch = TypingWatch(settle_seconds=5.0, clock=clock)
    watch.note_key()
    assert watch.typing() is True

    watch.clear()
    assert watch.typing() is False


def test_a_clock_that_jumps_backwards_does_not_confuse_it():
    """
    系統時間被往回調（校時、換時區）時，「距離上次按鍵幾秒」不能變成負數，
    否則會被當成剛剛才按過而永遠停住。
    """
    clock = FakeClock()
    watch = TypingWatch(settle_seconds=2.0, clock=clock)
    watch.note_key()
    clock.now -= 3600
    assert watch.seconds_since_key() == 0.0


@pytest.mark.parametrize("value,expected", [
    (0.1, MIN_SETTLE_SECONDS),
    (2.0, 2.0),
    (999.0, MAX_SETTLE_SECONDS),
    ("3", 3.0),
    (None, DEFAULT_SETTLE_SECONDS),
    ("nonsense", DEFAULT_SETTLE_SECONDS),
])
def test_the_settle_window_is_clamped(value, expected):
    assert clamp_settle_seconds(value) == expected


@pytest.mark.parametrize("behaviour", [BEHAVIOUR_FLOOR, BEHAVIOUR_WANDER, BEHAVIOUR_CHASE])
def test_a_settled_pet_does_not_move_in_any_behaviour(behaviour):
    """
    每一種行為都要停。閘門如果放在各分支裡，總有一種會漏掉，而漏掉的那一種
    就是使用者打字時還在螢幕上跑的那隻。
    """
    motion = PetMotion(x=100, y=100, width=64, height=64,
                       bounds=(0, 0, 1920, 1080), speed=5, behaviour=behaviour)
    motion.settled = True

    for _ in range(50):
        assert motion.step() == (100, 100)


@pytest.mark.parametrize("behaviour", [BEHAVIOUR_FLOOR, BEHAVIOUR_WANDER, BEHAVIOUR_CHASE])
def test_it_moves_again_once_released(behaviour):
    """停手之後一定要恢復走動——永遠停住的寵物看起來就是壞掉的。"""
    motion = PetMotion(x=100, y=100, width=64, height=64,
                       bounds=(0, 0, 1920, 1080), speed=5, behaviour=behaviour)
    # 追逐沒有目標時本來就不會動，所以要給它一個，否則這條測試對 chase 而言
    # 問的是「沒有目標會不會動」，而不是「放行之後會不會動」。
    # Chase does not move without a target, so it gets one: otherwise this test
    # asks chase whether it moves with nothing to chase, not whether releasing
    # it worked.
    if behaviour == BEHAVIOUR_CHASE:
        motion.target = (900.0, 700.0)
    motion.settled = True
    for _ in range(10):
        motion.step()

    motion.settled = False
    positions = {motion.step() for _ in range(60)}
    assert len(positions) > 1, "the pet never moved after being released"


def test_settling_does_not_change_where_the_pet_already_is():
    """安分是停在原地，不是回到某個預設位置。"""
    motion = PetMotion(x=742, y=310, width=64, height=64,
                       bounds=(0, 0, 1920, 1080), speed=5, behaviour=BEHAVIOUR_WANDER)
    motion.settled = True
    assert motion.step() == (742, 310)


def test_a_pet_is_not_settled_by_default():
    motion = PetMotion(x=0, y=0, width=64, height=64, bounds=(0, 0, 1920, 1080))
    assert motion.settled is False
