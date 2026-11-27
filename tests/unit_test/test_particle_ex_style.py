"""A failed extended-style read leaves the particle window's click-through alone (code review CR-05).

Every Win32 call is a fake: nothing here touches a real window.
"""
from frontengine.show.particle import particle_ui
from frontengine.show.particle.particle_ui import (
    GWL_EXSTYLE, WS_EX_LAYERED, ExStyleApi, ParticleOpenGLWidget, add_layered_style,
)

WS_EX_TRANSPARENT = 0x20
HWND = 0x1234


class FakeUser32:
    """GetWindowLong/SetWindowLong with a last error each call may set, as user32 does."""

    def __init__(self, style, read_error=0, write_error=0):
        self.style, self.read_error, self.write_error = style, read_error, write_error
        self.last_error, self.writes = 0, []

    def get_long(self, hwnd, index):
        assert (hwnd, index) == (HWND, GWL_EXSTYLE)
        if self.read_error:
            self.last_error = self.read_error
            return 0
        return self.style

    def set_long(self, hwnd, index, value):
        self.writes.append((hwnd, index, value))
        if self.write_error:
            self.last_error = self.write_error
            return 0
        previous, self.style = self.style, value
        return previous

    def set_last_error(self, value):
        self.last_error = value

    def api(self):
        return ExStyleApi(self.get_long, self.set_long, self.set_last_error, lambda: self.last_error)


def test_a_failed_read_writes_nothing(monkeypatch):
    warnings = []
    monkeypatch.setattr(particle_ui.front_engine_logger, "warning", warnings.append)
    user32 = FakeUser32(WS_EX_TRANSPARENT, read_error=1400)
    assert not add_layered_style(HWND, user32.api())
    assert user32.writes == [] and user32.style == WS_EX_TRANSPARENT
    assert len(warnings) == 1 and "1400" in warnings[0]


def test_a_stale_last_error_is_cleared_before_the_read():
    user32 = FakeUser32(WS_EX_TRANSPARENT)
    user32.last_error = 5  # left over from an unrelated call
    assert add_layered_style(HWND, user32.api())
    assert user32.style == WS_EX_TRANSPARENT | WS_EX_LAYERED


def test_a_window_without_extended_style_still_becomes_layered():
    user32 = FakeUser32(0)
    assert add_layered_style(HWND, user32.api())
    assert user32.writes == [(HWND, GWL_EXSTYLE, WS_EX_LAYERED)]


def test_existing_bits_are_kept_and_an_already_layered_window_is_not_rewritten():
    user32 = FakeUser32(WS_EX_TRANSPARENT | WS_EX_LAYERED)
    assert add_layered_style(HWND, user32.api())
    assert user32.writes == []


def test_a_failed_write_is_reported(monkeypatch):
    warnings = []
    monkeypatch.setattr(particle_ui.front_engine_logger, "warning", warnings.append)
    user32 = FakeUser32(WS_EX_TRANSPARENT, write_error=5)
    assert not add_layered_style(HWND, user32.api())
    assert len(warnings) == 1


def test_apply_winapi_uses_the_given_api_on_the_widgets_window():
    class Window:
        def winId(self):
            return HWND
    user32 = FakeUser32(WS_EX_TRANSPARENT, read_error=6)
    assert not ParticleOpenGLWidget.apply_winapi(Window(), user32.api())
    assert user32.writes == []
