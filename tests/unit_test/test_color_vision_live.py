"""The colour-vision layer: follows the screen without hiding itself, or is a still picture."""
import time

import numpy
from PySide6.QtCore import QRect
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from frontengine.show.screen_care import color_vision_widget
from frontengine.show.screen_care.color_vision_widget import ColorVisionWidget
from frontengine.utils.color_vision.color_vision import KIND_DEUTERANOPIA, KIND_PROTANOPIA, simulate_rgb
from frontengine.utils.color_vision.live_simulation import FrameSimulator, LiveSimulation, simulate_bgrx

GREEN = (0x20, 0xc0, 0x40)


def _frame(rgb, height=6, width=4):
    frame = numpy.zeros((height, width, 4), dtype=numpy.uint8)
    frame[:, :, :3] = rgb[::-1]
    return frame


class _Source:
    def __init__(self, frame):
        self.frame, self.grabs, self.closed = frame, 0, False

    def grab(self):
        self.grabs += 1
        return self.frame.copy()

    def close(self):
        self.closed = True


def _wait(condition, milliseconds=3000):
    deadline = time.monotonic() + milliseconds / 1000
    while not condition() and time.monotonic() < deadline:
        QTest.qWait(10)
    return condition()


def test_a_bgrx_frame_matches_the_single_colour_transform():
    result = simulate_bgrx(_frame(GREEN), KIND_DEUTERANOPIA, 1.0)
    assert tuple(int(value) for value in result[2, 2, :3][::-1]) == simulate_rgb(GREEN, KIND_DEUTERANOPIA)
    assert (result[:, :, 3] == 255).all()


def test_an_unchanged_frame_delivers_nothing_and_only_changed_rows_are_redone():
    simulator = FrameSimulator()
    frame = _frame(GREEN)
    first = simulator.transform(frame.copy(), KIND_DEUTERANOPIA, 1.0)
    assert first is not None
    assert simulator.transform(frame.copy(), KIND_DEUTERANOPIA, 1.0) is None
    frame[3, :, :3] = (9, 9, 200)
    second = simulator.transform(frame.copy(), KIND_DEUTERANOPIA, 1.0)
    assert (second[[0, 1, 2, 4, 5]] == first[[0, 1, 2, 4, 5]]).all()
    assert not (second[3] == first[3]).all()
    assert simulator.transform(frame.copy(), KIND_PROTANOPIA, 1.0) is not None      # a new setting redoes it all


def test_the_worker_stops_and_releases_its_source():
    source, delivered = _Source(_frame(GREEN)), []
    live = LiveSimulation(lambda: source, delivered.append, 0.005)
    live.set_simulation(KIND_DEUTERANOPIA, 1.0)
    live.start()
    assert _wait(lambda: source.grabs >= 5)
    live.stop()
    assert not live.running and source.closed
    assert len(delivered) == 1                       # a still screen is delivered once


def test_the_live_layer_never_hides_itself(monkeypatch):
    widget = ColorVisionWidget(KIND_DEUTERANOPIA)
    visibility, sources = [], []
    monkeypatch.setattr(widget, "setVisible", lambda shown: visibility.append(shown), raising=False)

    def open_source(_handle):
        sources.append(_Source(_frame(GREEN, 40, 60)))
        return sources[-1]

    widget.set_capture_boundary(lambda _widget, _excluded: True, open_source)
    widget.set_grabber(lambda rect: QPixmap())
    widget.setGeometry(QRect(0, 0, 60, 40))
    try:
        widget.start()
        assert widget.live
        assert _wait(lambda: widget.simulated is not None)
        QTest.qWait(150)
        assert False not in visibility               # hiding it was what made the screen flicker
        assert widget.simulated.toImage().pixelColor(5, 5).getRgb()[:3] == simulate_rgb(GREEN, KIND_DEUTERANOPIA)
        widget.set_simulation(KIND_PROTANOPIA)
        expected = simulate_rgb(GREEN, KIND_PROTANOPIA)
        assert _wait(lambda: widget.simulated.toImage().pixelColor(5, 5).getRgb()[:3] == expected)
    finally:
        widget.close()
    assert all(source.closed for source in sources)


def test_without_exclusion_it_is_a_still_picture_taken_while_off_screen(monkeypatch):
    monkeypatch.setattr(color_vision_widget, "HIDE_SETTLE_MS", 1)
    widget = ColorVisionWidget(KIND_DEUTERANOPIA)
    seen = []

    def grab(_rect):
        seen.append(widget.isVisible())
        pixmap = QPixmap(40, 30)
        pixmap.fill(QColor(*GREEN))
        return pixmap

    widget.set_capture_boundary(lambda _widget, _excluded: False, lambda _handle: None)
    widget.set_grabber(grab)
    widget.setGeometry(QRect(0, 0, 40, 30))
    try:
        widget.start()
        assert not widget.live and widget.isVisible()
        assert widget.simulated.toImage().pixelColor(5, 5).getRgb()[:3] == simulate_rgb(GREEN, KIND_DEUTERANOPIA)
        QTest.qWait(300)
        assert seen == [False]                       # no refresh timer: a still picture stays still
        widget.set_simulation(KIND_PROTANOPIA)
        assert _wait(lambda: len(seen) == 2 and widget.isVisible())
        assert seen == [False, False]
    finally:
        widget.close()


def test_a_still_picture_is_taken_again_when_the_layer_is_shown_again(monkeypatch):
    monkeypatch.setattr(color_vision_widget, "HIDE_SETTLE_MS", 1)
    widget = ColorVisionWidget(KIND_DEUTERANOPIA)
    seen = []

    def grab(_rect):
        seen.append(widget.isVisible())
        pixmap = QPixmap(40, 30)
        pixmap.fill(QColor(*GREEN))
        return pixmap

    widget.set_capture_boundary(lambda _widget, _excluded: False, lambda _handle: None)
    widget.set_grabber(grab)
    widget.setGeometry(QRect(0, 0, 40, 30))
    try:
        widget.start()
        widget.hide()
        QTest.qWait(50)
        assert seen == [False]
        widget.show()
        assert _wait(lambda: len(seen) == 2 and widget.isVisible())
        QTest.qWait(200)
        assert seen == [False, False] and widget.isVisible()     # once, and not in a circle
    finally:
        widget.close()


def test_the_picture_ignores_a_lowered_overlay_opacity():
    widget = ColorVisionWidget()
    widget.resize(10, 10)
    widget.simulated = QPixmap(10, 10)
    widget.simulated.fill(QColor(200, 10, 10))
    widget.set_ui_variable(0.2)
    assert widget._raster_content().pixelColor(5, 5).getRgb() == (200, 10, 10, 255)
    widget.close()


def test_hide_from_capture_off_leaves_the_exclusion_alone(make_main_window, monkeypatch):
    from frontengine.utils.screen_privacy import capture_affinity
    window = make_main_window()
    widget = ColorVisionWidget()
    changed = []
    monkeypatch.setattr(capture_affinity, "apply_to_widget", lambda target, excluded: changed.append(target) or True)
    window.screen_care_setting_ui.color_vision_widget_list.append(widget)
    try:
        window.control_center_ui.set_hide_from_capture(True)
        window.control_center_ui.set_hide_from_capture(False)
        assert widget not in changed
    finally:
        widget.close()
        window.screen_care_setting_ui.color_vision_widget_list.clear()
        QApplication.processEvents()
