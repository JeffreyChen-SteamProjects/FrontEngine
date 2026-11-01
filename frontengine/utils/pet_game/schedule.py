"""Game-day clock and daily routines, separate from wall-clock time.

One game day is sixty effective minutes: time only advances while the home is
running, so a routine is a rhythm of the game, not of the player's day.
"""
from __future__ import annotations

DAY_MS = 60 * 60 * 1000
HOUR_MS = DAY_MS // 24
START_HOUR = 8            # a new home starts in the morning
BLOCKS = ("sleep", "meal", "work", "free")

# Each template lists (start hour, end hour, block); unlisted hours are free.
# Ranges may wrap past midnight.
TEMPLATES: dict[str, tuple[tuple[int, int, str], ...]] = {
    "standard": ((23, 7, "sleep"), (7, 8, "meal"), (9, 12, "work"), (12, 13, "meal"),
                 (13, 17, "work"), (18, 19, "meal")),
    "early": ((21, 5, "sleep"), (5, 6, "meal"), (6, 11, "work"), (11, 12, "meal"),
              (12, 15, "work"), (17, 18, "meal")),
    "night": ((9, 17, "sleep"), (17, 18, "meal"), (19, 23, "work"), (23, 24, "meal"),
              (0, 3, "work")),
    "leisure": ((0, 8, "sleep"), (8, 9, "meal"), (10, 13, "work"), (13, 14, "meal"),
                (19, 20, "meal")),
}


def game_hour(time_ms: int) -> int:
    return (time_ms % DAY_MS) // HOUR_MS


def game_day(time_ms: int) -> int:
    return time_ms // DAY_MS + 1


def clock_text(time_ms: int) -> str:
    minutes = (time_ms % DAY_MS) * 24 * 60 // DAY_MS
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def block_at(template: str, hour: int) -> str:
    for start, end, block in TEMPLATES[template]:
        inside = start <= hour < end if start < end else (hour >= start or hour < end)
        if inside:
            return block
    return "free"


def initial_time() -> int:
    return START_HOUR * HOUR_MS
