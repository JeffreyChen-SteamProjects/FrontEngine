"""Smart pause: FrontEngine's own full-screen layers are not a program to stand aside for."""
import ctypes
import os
import sys

import pytest
from PySide6.QtWidgets import QWidget

from frontengine.show.canvas.whiteboard_widget import WhiteboardWidget
from frontengine.show.capture.region_capture import RegionCaptureWidget
from frontengine.show.freeze.freeze_widget import FreezeWidget
from frontengine.show.image.paint_image import ImageWidget
from frontengine.show.measure.measure_widget import MeasureWidget
from frontengine.show.presentation.annotation_overlay import AnnotationOverlay
from frontengine.show.presentation.cursor_effects import CursorEffectWidget
from frontengine.show.presentation.keystroke_display import KeystrokeDisplayWidget
from frontengine.show.presentation.magnifier import MagnifierWidget
from frontengine.show.screen_care.color_vision_widget import ColorVisionWidget
from frontengine.utils.smart_pause import smart_pause_service
from frontengine.utils.smart_pause.smart_pause_service import SmartPauseService, windows_fullscreen_detector


OWN, OTHER = os.getpid(), os.getpid() + 1
FULL, WINDOWED = (0, 0, 1920, 1080), (100, 100, 900, 700)


class _Window:
    def __init__(self, owner=OTHER, rect=FULL, *, tool=False, visible=True, iconic=False, name="SomeProgram"):
        self.owner, self.rect, self.tool = owner, rect, tool
        self.visible, self.iconic, self.name = visible, iconic, name


class _FakeUser32:
    """Windows from the top of the order down; the first one is in the foreground."""

    def __init__(self, *windows: _Window) -> None:
        self.windows = windows

    def _at(self, hwnd) -> _Window:
        return self.windows[hwnd - 1]

    @staticmethod
    def GetForegroundWindow():
        return 1

    def GetWindow(self, hwnd, _command):
        return hwnd + 1 if hwnd < len(self.windows) else 0

    def GetWindowLongW(self, hwnd, _index):
        return 0x80 if self._at(hwnd).tool else 0

    def IsWindowVisible(self, hwnd):
        return self._at(hwnd).visible

    def IsIconic(self, hwnd):
        return self._at(hwnd).iconic

    def GetWindowThreadProcessId(self, hwnd, reference):
        reference._obj.value = self._at(hwnd).owner
        return 1

    def GetClassNameW(self, hwnd, buffer, _size):
        buffer.value = self._at(hwnd).name

    def GetWindowRect(self, hwnd, reference):
        rect = reference._obj
        rect.left, rect.top, rect.right, rect.bottom = self._at(hwnd).rect
        return 1

    @staticmethod
    def MonitorFromWindow(_hwnd, _flag):
        return 1

    @staticmethod
    def GetMonitorInfoW(_monitor, reference):
        area = reference._obj.rcMonitor
        area.left, area.top, area.right, area.bottom = FULL
        return 1


LAYER, TOOLBAR = _Window(OWN, tool=True), _Window(OWN, WINDOWED, tool=True)


@pytest.mark.skipif(sys.platform != "win32", reason="Win32 foreground window")
@pytest.mark.parametrize("windows, expected", [
    ([_Window()], True),
    ([_Window(rect=WINDOWED)], False),
    ([LAYER], False),                                                   # over an empty desktop
    ([LAYER, _Window(rect=WINDOWED), _Window()], False),                # over an ordinary window
    ([LAYER, _Window()], True),                                         # drawing over a slide show
    ([TOOLBAR, LAYER, _Window()], True),                                # ... with its toolbar clicked
    ([LAYER, _Window(visible=False), _Window(iconic=True, rect=WINDOWED),
      _Window(rect=WINDOWED, tool=True), _Window()], True),
    ([LAYER, _Window(name="Progman")], False),                          # the desktop itself
    ([LAYER, _Window(OWN, WINDOWED), _Window()], False),                # over FrontEngine's own window
    ([_Window(OWN, WINDOWED), _Window()], False),                       # the settings window in front
])
def test_the_program_beneath_our_own_layers_decides(monkeypatch, windows, expected):
    monkeypatch.setattr(ctypes.windll, "user32", _FakeUser32(*windows))
    monkeypatch.setattr(smart_pause_service, "_is_cloaked", lambda _hwnd: False)
    assert windows_fullscreen_detector() is expected
    service = SmartPauseService(battery_provider=lambda: False, app_provider=lambda: None)
    seen = []
    service.pause_changed.connect(lambda paused, reason: seen.append((paused, reason)))
    service.poll_once()
    assert seen == ([(True, smart_pause_service.pause_reason({}, fullscreen=True))] if expected else [])


def test_drawing_over_a_full_screen_program_does_not_end_the_pause(monkeypatch):
    if sys.platform != "win32":
        pytest.skip("Win32 foreground window")
    monkeypatch.setattr(smart_pause_service, "_is_cloaked", lambda _hwnd: False)
    service = SmartPauseService(battery_provider=lambda: False, app_provider=lambda: None)
    seen = []
    service.pause_changed.connect(lambda paused, reason: seen.append(paused))
    for windows in ([_Window()], [LAYER, _Window()], [_Window()], [_Window(rect=WINDOWED)]):
        monkeypatch.setattr(ctypes.windll, "user32", _FakeUser32(*windows))
        service.poll_once()
    assert seen == [True, False]


def test_resuming_gives_back_only_what_smart_pause_took(make_main_window):
    window = make_main_window()
    hidden_by_hand, shown, sound = QWidget(), QWidget(), QWidget()
    sound.windowless = True
    window.image_setting_ui.image_widget_list.extend([hidden_by_hand, shown])
    window.sound_player_setting_ui.sound_widget_list.append(sound)
    shown.show()
    groups = []
    window.control_center_ui.overlay_visibility_changed.connect(groups.append)
    try:
        window._on_smart_pause_changed(True, "fullscreen")
        window._on_smart_pause_changed(False, "")
        assert shown.isVisible() and not hidden_by_hand.isVisible() and not sound.isVisible()
        assert groups == [True, False]
        window._on_smart_pause_changed(True, "fullscreen")
        window.control_center_ui.hide_all()                # the user's own choice, made meanwhile
        window._on_smart_pause_changed(False, "")
        assert not shown.isVisible() and groups[-1] is True
        window.control_center_ui.show_all()
        assert shown.isVisible() and hidden_by_hand.isVisible() and not sound.isVisible()
    finally:
        for widget in (hidden_by_hand, shown, sound):
            widget.close()
        window.image_setting_ui.image_widget_list.clear()
        window.sound_player_setting_ui.sound_widget_list.clear()


@pytest.mark.parametrize("kind", [AnnotationOverlay, WhiteboardWidget, CursorEffectWidget, KeystrokeDisplayWidget,
                                  MagnifierWidget, FreezeWidget, MeasureWidget, RegionCaptureWidget,
                                  ColorVisionWidget])
def test_tools_in_use_are_marked_to_stay(kind):
    assert kind.stays_while_paused is True


def test_smart_pause_hides_shown_overlays_but_not_the_tools_in_use(make_main_window):
    window = make_main_window()
    page = window.presentation_setting_ui
    page.start_annotation()
    layer = page.annotation_widget_list[0]
    other = QWidget()
    window.image_setting_ui.image_widget_list.append(other)
    other.show()
    try:
        assert getattr(ImageWidget, "stays_while_paused") is False
        window._on_smart_pause_changed(True, "fullscreen")
        assert layer.isVisible() and not other.isVisible()
        window._on_smart_pause_changed(False, "")
        assert layer.isVisible() and other.isVisible()
        layer.finish_requested.emit()
        assert page.annotation_widget_list == []
    finally:
        other.close()
        window.image_setting_ui.image_widget_list.clear()
