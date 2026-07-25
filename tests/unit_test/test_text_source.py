"""
動態文字來源的純邏輯測試（時間與資料都用注入的假 provider，不碰真實系統或網路）。
Pure-logic tests for dynamic text sources — time and data come from injected
fakes, so nothing touches the real system or the network.
"""
from datetime import datetime, timedelta

from frontengine.utils.text_source.text_source import (
    DEFAULT_TEMPLATES, SOURCE_CLOCK, SOURCE_COUNTDOWN, SOURCE_DATE, SOURCE_KINDS, SOURCE_STATIC,
    SOURCE_STOPWATCH, SOURCE_SYSTEM, SOURCE_WEATHER, TextSource, format_duration, format_mapping,
    parse_countdown_target,
)

NOW = datetime(2026, 7, 25, 14, 30, 5)


class Clock:
    """可控制的時鐘 / A clock the test can advance."""

    def __init__(self, start: datetime = NOW) -> None:
        self.now = start

    def __call__(self) -> datetime:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now = self.now + timedelta(seconds=seconds)


# --- format_duration ------------------------------------------------------
def test_format_duration_shapes() -> None:
    assert format_duration(0) == "00:00"
    assert format_duration(65) == "01:05"
    assert format_duration(3661) == "1:01:01"
    assert format_duration(-30) == "00:00", "negative time reads as zero"
    assert format_duration("junk") == "00:00"


# --- parse_countdown_target ----------------------------------------------
def test_countdown_accepts_minutes() -> None:
    assert parse_countdown_target("25", NOW) == NOW + timedelta(minutes=25)
    assert parse_countdown_target("0.5", NOW) == NOW + timedelta(seconds=30)


def test_countdown_accepts_a_clock_time_and_rolls_over_midnight() -> None:
    assert parse_countdown_target("15:00", NOW) == NOW.replace(hour=15, minute=0, second=0, microsecond=0)
    tomorrow = parse_countdown_target("09:00", NOW)
    assert tomorrow.day == NOW.day + 1 and tomorrow.hour == 9


def test_countdown_accepts_a_full_date() -> None:
    assert parse_countdown_target("2026-12-31 23:59", NOW) == datetime(2026, 12, 31, 23, 59)
    assert parse_countdown_target("2026-12-31", NOW) == datetime(2026, 12, 31)


def test_countdown_rejects_nonsense() -> None:
    assert parse_countdown_target("", NOW) is None
    assert parse_countdown_target("not a time", NOW) is None
    assert parse_countdown_target(None, NOW) is None


# --- format_mapping -------------------------------------------------------
def test_format_mapping_fills_and_falls_back() -> None:
    values = {"cpu": 12, "ram": 34}
    assert format_mapping("CPU {cpu}", values, "fallback {ram}") == "CPU 12"
    assert format_mapping("", values, "fallback {ram}") == "fallback 34"
    assert format_mapping("{missing}", values, "fallback {ram}") == "fallback 34"
    assert format_mapping("{missing}", values, "{alsomissing}") == ""


# --- TextSource -----------------------------------------------------------
def test_static_source_returns_its_text() -> None:
    source = TextSource(SOURCE_STATIC, "hello", now_provider=Clock())
    assert source.text() == "hello"
    assert source.refresh_interval_ms == 0, "static text needs no timer"


def test_clock_and_date_use_strftime() -> None:
    clock = Clock()
    assert TextSource(SOURCE_CLOCK, "%H:%M:%S", now_provider=clock).text() == "14:30:05"
    assert TextSource(SOURCE_DATE, "%Y-%m-%d", now_provider=clock).text() == "2026-07-25"
    assert TextSource(SOURCE_CLOCK, "", now_provider=clock).text() == "14:30:05", "blank uses the default"


def test_clock_survives_a_broken_format() -> None:
    source = TextSource(SOURCE_CLOCK, "%Q", now_provider=Clock())
    assert isinstance(source.text(), str)


def test_countdown_counts_down_and_stops_at_zero() -> None:
    clock = Clock()
    source = TextSource(SOURCE_COUNTDOWN, "1", now_provider=clock)
    source.start()
    assert source.text() == "01:00"
    clock.advance(45)
    assert source.text() == "00:15"
    assert source.finished() is False
    clock.advance(30)
    assert source.text() == "00:00", "it floors at zero instead of going negative"
    assert source.finished() is True


def test_stopwatch_counts_up_from_start() -> None:
    clock = Clock()
    source = TextSource(SOURCE_STOPWATCH, now_provider=clock)
    source.start()
    assert source.text() == "00:00"
    clock.advance(75)
    assert source.text() == "01:15"


def test_system_source_fills_the_template() -> None:
    source = TextSource(SOURCE_SYSTEM, "CPU {cpu}% RAM {ram}%",
                        stats_provider=lambda: {"cpu": 12.5, "ram": 40.0})
    assert source.text() == "CPU 12.5% RAM 40.0%"


def test_missing_fields_read_as_unavailable() -> None:
    source = TextSource(SOURCE_SYSTEM, "CPU {cpu}%", stats_provider=lambda: {"cpu": None})
    assert source.text() == "CPU --%"


def test_absent_or_failing_providers_degrade() -> None:
    assert TextSource(SOURCE_SYSTEM, "{cpu}").text() == TextSource.UNAVAILABLE
    assert TextSource(SOURCE_WEATHER, "{temperature}", weather_provider=lambda: {}).text() == \
        TextSource.UNAVAILABLE

    def boom():
        raise RuntimeError("no data")

    assert TextSource(SOURCE_SYSTEM, "{cpu}", stats_provider=boom).text() == TextSource.UNAVAILABLE


def test_weather_source_fills_the_template() -> None:
    source = TextSource(SOURCE_WEATHER, "{temperature}{unit} {description}",
                        weather_provider=lambda: {"temperature": 30.0, "unit": "°C",
                                                  "description": "Partly cloudy"})
    assert source.text() == "30.0°C Partly cloudy"


def test_unknown_kind_falls_back_to_static() -> None:
    assert TextSource("nonsense", "text").kind == SOURCE_STATIC


def test_every_kind_has_a_default_and_an_interval() -> None:
    for kind in SOURCE_KINDS:
        assert kind in DEFAULT_TEMPLATES
        assert TextSource(kind).refresh_interval_ms >= 0
