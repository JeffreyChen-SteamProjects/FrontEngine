"""
專注計時器的純狀態機測試（時間由注入的時鐘控制）。
Pure state-machine tests for the focus timer, driven by an injected clock.
"""
from datetime import datetime, timedelta

from frontengine.utils.focus_timer.focus_timer import (
    PHASE_BREAK, PHASE_FOCUS, PHASE_IDLE, PHASE_LONG_BREAK, FocusTimer, clamp_minutes,
)

START = datetime(2026, 7, 25, 9, 0, 0)


class Clock:
    def __init__(self, start: datetime = START) -> None:
        self.now = start

    def __call__(self) -> datetime:
        return self.now

    def advance(self, minutes: float) -> None:
        self.now = self.now + timedelta(minutes=minutes)


def _timer(clock: Clock, **kwargs) -> FocusTimer:
    options = dict(focus_minutes=25, break_minutes=5, long_break_minutes=15, rounds=4)
    options.update(kwargs)
    return FocusTimer(now_provider=clock, **options)


def test_clamp_minutes() -> None:
    assert clamp_minutes(25, 5) == 25
    assert clamp_minutes(0, 5) == 1, "clamped to at least a minute"
    assert clamp_minutes(9999, 5) == 180, "clamped to a sane maximum"
    assert clamp_minutes("nonsense", 5) == 5
    assert clamp_minutes(None, 7) == 7


def test_starts_idle() -> None:
    timer = _timer(Clock())
    assert timer.phase == PHASE_IDLE
    assert timer.running is False
    assert timer.remaining_seconds() == 0.0
    assert timer.tick() is None, "an idle timer never changes phase"


def test_start_enters_focus_with_the_full_time() -> None:
    clock = Clock()
    timer = _timer(clock)
    assert timer.start() == PHASE_FOCUS
    assert timer.running is True
    assert timer.remaining_seconds() == 25 * 60


def test_time_counts_down_without_changing_phase() -> None:
    clock = Clock()
    timer = _timer(clock)
    timer.start()
    clock.advance(10)
    assert timer.tick() is None
    assert timer.remaining_seconds() == 15 * 60
    assert timer.phase == PHASE_FOCUS


def test_focus_rolls_into_a_break() -> None:
    clock = Clock()
    timer = _timer(clock)
    timer.start()
    clock.advance(25)
    assert timer.tick() == PHASE_BREAK
    assert timer.completed_focus == 1
    assert timer.remaining_seconds() == 5 * 60


def test_break_rolls_back_into_focus() -> None:
    clock = Clock()
    timer = _timer(clock)
    timer.start()
    clock.advance(25)
    timer.tick()
    clock.advance(5)
    assert timer.tick() == PHASE_FOCUS
    assert timer.completed_focus == 1, "a break is not a completed focus round"


def test_a_long_break_arrives_after_the_configured_rounds() -> None:
    clock = Clock()
    timer = _timer(clock, rounds=2)
    timer.start()
    clock.advance(25)
    assert timer.tick() == PHASE_BREAK
    clock.advance(5)
    timer.tick()
    clock.advance(25)
    assert timer.tick() == PHASE_LONG_BREAK
    assert timer.completed_focus == 2
    assert timer.remaining_seconds() == 15 * 60


def test_next_phase_is_predictable_without_advancing() -> None:
    clock = Clock()
    timer = _timer(clock, rounds=1)
    timer.start()
    assert timer.next_phase() == PHASE_LONG_BREAK, "every round ends long with rounds=1"
    assert timer.phase == PHASE_FOCUS, "asking must not change the phase"


def test_stop_returns_to_idle() -> None:
    clock = Clock()
    timer = _timer(clock)
    timer.start()
    timer.stop()
    assert timer.phase == PHASE_IDLE
    assert timer.running is False
    clock.advance(60)
    assert timer.tick() is None


def test_restarting_resets_the_rounds() -> None:
    clock = Clock()
    timer = _timer(clock, rounds=2)
    timer.start()
    clock.advance(25)
    timer.tick()
    assert timer.completed_focus == 1
    timer.start()
    assert timer.completed_focus == 0
    assert timer.phase == PHASE_FOCUS


def test_bad_settings_fall_back_instead_of_raising() -> None:
    timer = FocusTimer(focus_minutes="x", break_minutes=None, rounds="many", now_provider=Clock())
    assert timer.focus_minutes == 25
    assert timer.break_minutes == 5
    assert timer.rounds == 4
