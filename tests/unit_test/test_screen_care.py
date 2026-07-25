"""
護眼功能的純邏輯測試：濾鏡濃度夾制、閱讀尺亮帶位置、休息提醒狀態機。
Pure-logic tests for the eye-care features: filter strength clamping, the
reading ruler's band placement, and the break-reminder state machine.
"""
from datetime import datetime, timedelta

from frontengine.show.screen_care.screen_filter import (
    DEFAULT_FILTER_COLOR, FILTER_COLORS, MAX_STRENGTH, MIN_STRENGTH, clamp_strength, ruler_band,
)
from frontengine.utils.break_reminder.break_reminder import (
    PHASE_IDLE, PHASE_REST, PHASE_WORK, BreakReminder, clamp_minutes, clamp_seconds,
)

START = datetime(2026, 7, 25, 10, 0, 0)


class Clock:
    def __init__(self, start: datetime = START) -> None:
        self.now = start

    def __call__(self) -> datetime:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now = self.now + timedelta(seconds=seconds)


# --- filter ---------------------------------------------------------------
def test_filter_strength_is_clamped_to_something_usable() -> None:
    assert clamp_strength(15) == 15
    assert clamp_strength(0) == MIN_STRENGTH, "a filter you cannot see is not useful"
    assert clamp_strength(500) == MAX_STRENGTH, "a filter you cannot see through is worse"
    assert clamp_strength("dark") == 15
    assert clamp_strength(None, fallback=40) == 40


def test_filter_palette_is_usable() -> None:
    names = [name for name, _hex in FILTER_COLORS]
    assert "Warm" in names, "warm dimming is the common case"
    assert len(FILTER_COLORS) >= 5
    assert all(value.startswith("#") and len(value) == 7 for _name, value in FILTER_COLORS)
    assert DEFAULT_FILTER_COLOR in [value for _name, value in FILTER_COLORS]


# --- reading ruler --------------------------------------------------------
def test_band_centres_on_the_cursor() -> None:
    assert ruler_band(500, 1000, 100) == (450, 550)


def test_band_stays_on_screen_at_the_top() -> None:
    top, bottom = ruler_band(10, 1000, 100)
    assert top == 0 and bottom == 100


def test_band_stays_on_screen_at_the_bottom() -> None:
    top, bottom = ruler_band(990, 1000, 100)
    assert bottom <= 1000 and bottom - top == 100


def test_band_has_a_minimum_height() -> None:
    top, bottom = ruler_band(500, 1000, 1)
    assert bottom - top >= 10


def test_band_on_a_short_screen() -> None:
    top, bottom = ruler_band(20, 50, 100)
    assert top == 0 and bottom >= 50, "a band taller than the screen covers all of it"


# --- break reminder -------------------------------------------------------
def test_clamps() -> None:
    assert clamp_minutes(20) == 20
    assert clamp_minutes(0) == 1
    assert clamp_minutes("x") == 20
    assert clamp_seconds(20) == 20
    assert clamp_seconds(1) == 5
    assert clamp_seconds(None) == 20


def test_starts_idle_and_then_works() -> None:
    reminder = BreakReminder(now_provider=Clock())
    assert reminder.phase == PHASE_IDLE
    assert reminder.running is False
    assert reminder.start() == PHASE_WORK
    assert reminder.remaining_seconds() == 20 * 60


def test_work_turns_into_a_rest() -> None:
    clock = Clock()
    reminder = BreakReminder(work_minutes=20, rest_seconds=20, now_provider=clock)
    reminder.start()
    clock.advance(19 * 60)
    assert reminder.tick() is None
    clock.advance(60)
    assert reminder.tick() == PHASE_REST
    assert reminder.remaining_seconds() == 20


def test_rest_turns_back_into_work_and_counts_the_break() -> None:
    clock = Clock()
    reminder = BreakReminder(work_minutes=1, rest_seconds=20, now_provider=clock)
    reminder.start()
    clock.advance(60)
    reminder.tick()
    clock.advance(20)
    assert reminder.tick() == PHASE_WORK
    assert reminder.completed_breaks == 1


def test_stopping_ends_everything() -> None:
    clock = Clock()
    reminder = BreakReminder(work_minutes=1, now_provider=clock)
    reminder.start()
    reminder.stop()
    clock.advance(3600)
    assert reminder.tick() is None
    assert reminder.phase == PHASE_IDLE


def test_snoozing_returns_to_work_for_a_while() -> None:
    clock = Clock()
    reminder = BreakReminder(work_minutes=20, rest_seconds=20, now_provider=clock)
    reminder.start()
    clock.advance(20 * 60)
    reminder.tick()
    assert reminder.phase == PHASE_REST
    reminder.snooze(5)
    assert reminder.phase == PHASE_WORK
    assert reminder.remaining_seconds() == 5 * 60


def test_bad_settings_fall_back() -> None:
    reminder = BreakReminder(work_minutes="soon", rest_seconds=None, now_provider=Clock())
    assert reminder.work_minutes == 20
    assert reminder.rest_seconds == 20
