"""Time of day and weather: atmosphere only, derived from the game clock and the home identity.

Weather never damages furniture, never blocks anything and never has to be
waited for. It is seeded from the home and the game day, not from the
simulation's random stream, so looking at the sky cannot change a replay.
"""
from __future__ import annotations

import hashlib

from frontengine.utils.pet_game.schedule import DAY_MS, HOUR_MS, game_day, game_hour

SKY_PHASES = ("dawn", "day", "dusk", "night")
WEATHERS = ("clear", "cloudy", "rain", "snow")      # snow is winter's rain
SEASONS = ("spring", "summer", "autumn", "winter")
SEASON_DAYS = 7
YEAR_DAYS = SEASON_DAYS * len(SEASONS)
WEATHER_WEIGHTS = (5, 3, 2)
WEATHER_SPAN_HOURS = 6                      # weather may change four times a game day


def sky(time_ms: int) -> str:
    hour = game_hour(time_ms)
    if 5 <= hour < 7:
        return "dawn"
    if 7 <= hour < 17:
        return "day"
    if 17 <= hour < 19:
        return "dusk"
    return "night"


def daylight(time_ms: int) -> float:
    """0 at midnight, 1 at noon, smooth between, for tinting the drawing."""
    minutes = (time_ms % DAY_MS) * 24 * 60 // DAY_MS
    distance = abs(minutes - 12 * 60) / (12 * 60)
    return max(0.0, min(1.0, 1.25 - distance * 1.5))


def season(time_ms: int) -> str:
    """Seven game days each; the year turns every four weeks and nothing is ever missed for good."""
    return SEASONS[((game_day(time_ms) - 1) % YEAR_DAYS) // SEASON_DAYS]


def weather(home: str, time_ms: int) -> str:
    current = _weather(home, time_ms)
    return "snow" if current == "rain" and season(time_ms) == "winter" else current


def _weather(home: str, time_ms: int) -> str:
    span = game_hour(time_ms) // WEATHER_SPAN_HOURS
    digest = hashlib.sha256(f"{home}|weather|{game_day(time_ms)}|{span}".encode("ascii")).digest()
    roll = int.from_bytes(digest[:4], "big") % sum(WEATHER_WEIGHTS)
    for name, weight in zip(WEATHERS[:3], WEATHER_WEIGHTS):
        if roll < weight:
            return name
        roll -= weight
    return WEATHERS[0]  # pragma: no cover


def next_change_ms(time_ms: int) -> int:
    span_ms = WEATHER_SPAN_HOURS * HOUR_MS
    return (time_ms // span_ms + 1) * span_ms
