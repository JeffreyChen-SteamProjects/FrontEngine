"""
看板輪播、無限畫布與麥克風電表的純邏輯測試。
Pure-logic tests for signage rotation, the infinite canvas and the microphone
meter.
"""
from datetime import datetime, timedelta

from frontengine.show.canvas.whiteboard_widget import (
    DEFAULT_COLOR, MAX_ZOOM, MIN_ZOOM, clamp_zoom, content_bounds, to_canvas, to_screen,
)
from frontengine.utils.audio_meter.microphone_meter import (
    MicrophoneMeter, list_input_devices, microphone_level,
)
from frontengine.utils.signage.signage_service import (
    DEFAULT_INTERVAL_MINUTES, MAX_INTERVAL_MINUTES, MIN_INTERVAL_MINUTES, SignageService,
    clamp_interval, normalize_playlist,
)

START = datetime(2026, 7, 26, 9, 0)


# --- signage --------------------------------------------------------------
def test_the_interval_is_clamped() -> None:
    assert clamp_interval(0) == MIN_INTERVAL_MINUTES
    assert clamp_interval(10 ** 6) == MAX_INTERVAL_MINUTES
    assert clamp_interval("nonsense") == DEFAULT_INTERVAL_MINUTES


def test_the_playlist_drops_blanks_and_duplicates_but_keeps_order() -> None:
    assert normalize_playlist("morning, noon,, morning\nevening") == \
        ["morning", "noon", "evening"]
    assert normalize_playlist(["a", " ", "a", "b"]) == ["a", "b"]
    assert normalize_playlist(5) == []


def service_at(clock, config):
    return SignageService(config_provider=lambda: config["value"],
                          now_provider=lambda: clock["now"])


def test_rotation_shows_the_first_preset_then_advances_when_due() -> None:
    clock = {"now": START}
    config = {"value": {"presets": ["a", "b"], "interval_minutes": 5}}
    shown = []
    service = service_at(clock, config)
    service.preset_due.connect(shown.append)

    assert service.start() == "a"
    service.poll_once()
    assert shown == ["a"], "nothing new before it is due"

    clock["now"] += timedelta(minutes=6)
    service.poll_once()
    assert shown == ["a", "b"]


def test_the_rotation_wraps_at_the_end() -> None:
    clock = {"now": START}
    config = {"value": {"presets": ["a", "b"], "interval_minutes": 1}}
    shown = []
    service = service_at(clock, config)
    service.preset_due.connect(shown.append)
    service.start()
    for _ in range(3):
        clock["now"] += timedelta(minutes=2)
        service.poll_once()
    assert shown == ["a", "b", "a", "b"]


def test_an_empty_playlist_starts_nothing() -> None:
    service = SignageService(config_provider=lambda: {"presets": []},
                             now_provider=lambda: START)
    assert service.start() is None
    assert service.running is False


def test_stopping_ends_the_rotation() -> None:
    clock = {"now": START}
    config = {"value": {"presets": ["a", "b"], "interval_minutes": 1}}
    shown = []
    service = service_at(clock, config)
    service.preset_due.connect(shown.append)
    service.start()
    service.stop()
    clock["now"] += timedelta(minutes=5)
    service.poll_once()
    assert shown == ["a"]


def test_the_time_left_counts_down() -> None:
    clock = {"now": START}
    config = {"value": {"presets": ["a"], "interval_minutes": 10}}
    service = service_at(clock, config)
    service.start()
    assert service.rotation.seconds_left() == 600
    clock["now"] += timedelta(minutes=4)
    assert service.rotation.seconds_left() == 360


# --- the infinite canvas --------------------------------------------------
def test_zoom_is_clamped() -> None:
    assert clamp_zoom(0.01) == MIN_ZOOM
    assert clamp_zoom(99) == MAX_ZOOM
    assert clamp_zoom("nonsense") == 1.0


def test_screen_and_canvas_coordinates_round_trip() -> None:
    for zoom in (0.5, 1.0, 2.5):
        for offset in ((0, 0), (37, -18)):
            assert to_canvas(to_screen((10, 20), offset, zoom), offset, zoom) == (10.0, 20.0)


def test_panning_moves_the_view_not_the_drawing() -> None:
    """同一個畫布座標，平移後在螢幕上的位置會變，但畫布座標本身不變。"""
    canvas_point = (100.0, 50.0)
    before = to_screen(canvas_point, (0, 0), 1.0)
    after = to_screen(canvas_point, (40, 25), 1.0)
    assert after == (before[0] + 40, before[1] + 25)


def test_bounds_cover_every_stroke() -> None:
    strokes = [{"points": [(0, 0), (10, 40)]}, {"points": [(-5, 20), (30, 25)]}]
    assert content_bounds(strokes) == (-5, 0, 30, 40)


def test_nothing_drawn_has_no_bounds() -> None:
    assert content_bounds([]) is None
    assert content_bounds([{"points": []}]) is None


def test_the_default_colour_is_a_real_colour() -> None:
    from PySide6.QtGui import QColor

    assert QColor(DEFAULT_COLOR).isValid()


# --- microphone meter -----------------------------------------------------
def test_listing_inputs_returns_pairs() -> None:
    assert all(isinstance(entry, tuple) and len(entry) == 2 for entry in list_input_devices())


def test_a_level_is_a_fraction_or_nothing() -> None:
    level = microphone_level()
    assert level is None or 0.0 <= level <= 1.0


def test_an_unknown_device_degrades_to_nothing() -> None:
    meter = MicrophoneMeter(device_id="not-a-real-device")
    assert meter.level() is None
    meter.close()


def test_closing_twice_is_safe() -> None:
    meter = MicrophoneMeter(device_id="not-a-real-device")
    meter.close()
    meter.close()
    assert meter.level() is None
