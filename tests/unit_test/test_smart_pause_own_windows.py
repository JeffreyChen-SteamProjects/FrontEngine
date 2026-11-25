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


class _FakeUser32:
    """A full-screen foreground window owned by ``owner``."""

    def __init__(self, owner: int) -> None:
        self.owner = owner

    @staticmethod
    def GetForegroundWindow():
        return 4242

    def GetWindowThreadProcessId(self, _hwnd, reference):
        reference._obj.value = self.owner
        return 1

    @staticmethod
    def GetClassNameW(_hwnd, buffer, _size):
        buffer.value = "SomeProgram"

    @staticmethod
    def GetWindowRect(_hwnd, reference):
        rect = reference._obj
        rect.left, rect.top, rect.right, rect.bottom = 0, 0, 1920, 1080
        return 1

    @staticmethod
    def MonitorFromWindow(_hwnd, _flag):
        return 1

    @staticmethod
    def GetMonitorInfoW(_monitor, reference):
        area = reference._obj.rcMonitor
        area.left, area.top, area.right, area.bottom = 0, 0, 1920, 1080
        return 1


@pytest.mark.skipif(sys.platform != "win32", reason="Win32 foreground window")
@pytest.mark.parametrize("own, expected", [(True, False), (False, True)])
def test_only_another_programs_full_screen_window_pauses(monkeypatch, own, expected):
    owner = os.getpid() if own else os.getpid() + 1
    monkeypatch.setattr(ctypes.windll, "user32", _FakeUser32(owner))
    assert windows_fullscreen_detector() is expected
    service = SmartPauseService(battery_provider=lambda: False, app_provider=lambda: None)
    seen = []
    service.pause_changed.connect(lambda paused, reason: seen.append((paused, reason)))
    service.poll_once()
    assert seen == ([(True, smart_pause_service.pause_reason({}, fullscreen=True))] if expected else [])


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
