"""Periodic samplers log a failing provider once when it starts failing (code review CR-04)."""
import pytest

from frontengine.utils.logging import loggin_instance
from frontengine.utils.logging.loggin_instance import FailureOnce


class Flaky:
    """A provider that raises while ``failing`` is set and returns ``value`` otherwise."""

    def __init__(self, value):
        self.value, self.failing = value, True

    def __call__(self):
        if self.failing:
            raise OSError("device gone")
        return self.value


def _focus_shield(provider):
    from frontengine.show.focus_shield.focus_shield_widget import DimBackgroundWidget
    widget = DimBackgroundWidget()
    widget.set_window_provider(provider)
    return widget, widget.refresh


def _reading_ruler(provider):
    from frontengine.show.screen_care.screen_filter import ReadingRulerWidget
    widget = ReadingRulerWidget()
    widget.set_cursor_provider(provider)
    return widget, widget.follow_cursor


def _spectrum(provider):
    from frontengine.show.spectrum.spectrum_widget import SpectrumWidget
    widget = SpectrumWidget()
    widget.set_level_provider(provider)
    return widget, widget.refresh


def _wallpaper(provider):
    from frontengine.show.wallpaper.wallpaper_widget import WallpaperWidget
    widget = WallpaperWidget(audio_react=True)
    widget.set_audio_level_provider(provider)
    return widget, widget._update_scale


SAMPLERS = {
    "focus_shield": (_focus_shield, (10, 10, 100, 100)),
    "reading_ruler": (_reading_ruler, 120),
    "spectrum": (_spectrum, [0.5] * 16),
    "wallpaper": (_wallpaper, 0.4),
}


@pytest.fixture()
def warnings(monkeypatch):
    logged = []
    monkeypatch.setattr(loggin_instance.front_engine_logger, "warning", logged.append)
    return logged


@pytest.mark.parametrize("name", SAMPLERS)
def test_a_repeated_failure_logs_once_and_a_failure_after_recovery_logs_again(name, warnings):
    build, value = SAMPLERS[name]
    provider = Flaky(value)
    widget, poll = build(provider)
    try:
        for _ in range(5):
            poll()
        assert len(warnings) == 1 and "OSError: device gone" in warnings[0]
        provider.failing = False
        poll()
        poll()
        assert len(warnings) == 1
        provider.failing = True
        poll()
        poll()
        assert len(warnings) == 2
    finally:
        widget.close()


def test_failure_once_uses_an_injected_log():
    logged = []
    latch = FailureOnce("Source", "sampling", logged.append)
    latch.failed(ValueError("bad"))
    latch.failed(ValueError("worse"))
    latch.recovered()
    latch.failed(RuntimeError("again"))
    assert logged == [
        "[Source] sampling failed, the overlay degrades until it recovers: ValueError: bad",
        "[Source] sampling failed, the overlay degrades until it recovers: RuntimeError: again"]
