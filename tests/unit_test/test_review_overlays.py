"""Overlays: what the whole-project review found."""
from datetime import datetime, timedelta

import pytest
from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPixmap
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QWidget

from frontengine.show.base_widget import BaseWidget
from frontengine.show.focus_shield.focus_shield_widget import to_logical
from frontengine.show.image.paint_image import ImageWidget
from frontengine.show.pinned.pinned_image import PinnedImageWidget
from frontengine.show.presentation.keystroke_display import KeystrokeDisplayWidget
from frontengine.show.presentation.magnifier import MagnifierWidget
from frontengine.show.replica.replica_widget import WindowReplicaWidget
from frontengine.show.shortcuts.shortcut_sheet import ShortcutSheetWidget
from frontengine.show.wallpaper.wallpaper_widget import WallpaperWidget
from frontengine.user_setting.user_setting_file import save_overlay_geometry, user_setting_dict
from frontengine.utils.preset_schedule.preset_schedule_service import PresetScheduleService
from frontengine.utils.reminder.reminder_service import ReminderTracker
from frontengine.utils.weather import weather_service
from frontengine.utils.weather.weather_service import WeatherService


def _pixel(widget, x, y):
    return widget._raster_content().pixelColor(x, y)


def test_the_keystroke_display_shows_nothing_but_its_panel():
    widget = KeystrokeDisplayWidget()
    widget.resize(400, 200)
    assert _pixel(widget, 10, 10).alpha() == 0 and _pixel(widget, 200, 180).alpha() == 0
    widget.push_keys(["a"])
    image = widget._raster_content()
    assert any(image.pixelColor(x, y).alpha() for x in range(0, 400, 4) for y in range(0, 200, 4))
    assert image.pixelColor(5, 5).alpha() == 0
    widget.set_background_color("#00ff00")          # the chroma key is still the chroma key
    assert _pixel(widget, 5, 5) == QColor("#00ff00")
    widget.close()


def test_the_shortcut_sheet_is_as_see_through_as_it_says():
    widget = ShortcutSheetWidget([("Ctrl", "x")], opacity=1.0)
    widget.resize(300, 200)
    assert _pixel(widget, 290, 190).alpha() == 210
    widget.close()


def _gif(path):
    from PIL import Image
    frames = [Image.new("RGB", (8, 8), color) for color in ("red", "blue")]
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=40, loop=0)


def test_an_animated_wallpaper_moves(tmp_path):
    pytest.importorskip("PIL")
    _gif(tmp_path / "a.gif")
    widget = WallpaperWidget(str(tmp_path / "a.gif"))
    painted = []
    widget.update = lambda *_args: painted.append(True)
    QTest.qWait(400)
    assert len(painted) >= 3
    widget.close()


def test_a_video_wallpaper_paints_its_frames_and_lets_go(tmp_path, monkeypatch):
    played = []
    monkeypatch.setattr(WallpaperWidget, "_play_video", lambda self, path: played.append(path))
    (tmp_path / "a.mp4").write_bytes(b"x")
    widget = WallpaperWidget()
    assert widget.set_media(str(tmp_path / "a.mp4")) and played == [tmp_path / "a.mp4"]

    class Frame:
        @staticmethod
        def toImage():
            image = QImage(4, 4, QImage.Format.Format_RGB32)
            image.fill(QColor("red"))
            return image
    widget._show_frame(Frame())
    assert widget.current_pixmap().toImage().pixelColor(1, 1) == QColor("red")
    widget.close()


def test_a_wallpaper_list_skips_what_cannot_be_shown(make_main_window):
    page = make_main_window().wallpaper_setting_ui
    from frontengine.utils.playlist.playlist import Playlist

    class Widget:
        shown = []

        def set_media(self, path):
            self.shown.append(path)
            return path == "good"
    widget = Widget()
    assert page._show_next(widget, Playlist(["bad", "worse", "good"])) and widget.shown == ["bad", "worse", "good"]
    assert page._show_next(widget, Playlist(["bad"])) is False


def test_a_slideshow_stays_full_screen_and_keeps_its_picture_over_a_broken_one(tmp_path):
    for name, size in (("a.png", (80, 80)), ("b.png", (30, 15))):
        image = QImage(*size, QImage.Format.Format_RGB32)
        image.fill(QColor("red"))
        image.save(str(tmp_path / name))
    (tmp_path / "broken.png").write_bytes(b"not a picture")
    widget = ImageWidget(str(tmp_path / "a.png"))
    widget.showFullScreen()
    size = widget.size()
    assert widget.set_image_path(str(tmp_path / "b.png"))
    assert widget.isFullScreen() and widget.size() == size
    assert widget.set_image_path(str(tmp_path / "broken.png")) is False
    assert widget.image.width() == 30 and widget.size() == size
    widget.close()


def test_the_magnifier_counts_from_the_corner_of_the_screen_it_grabs(monkeypatch):
    asked = []

    class Screen:
        @staticmethod
        def geometry():
            return QRect(1920, -200, 1536, 864)

        @staticmethod
        def grabWindow(*arguments):
            asked.append(arguments)
            return QPixmap(1, 1)
    monkeypatch.setattr(QGuiApplication, "screenAt", staticmethod(lambda _point: Screen))
    MagnifierWidget._grab_screen(QRect(2000, -100, 50, 40))
    assert asked == [(0, 80, 100, 50, 40)]


def test_a_window_on_a_scaled_second_monitor_is_found_where_it_is():
    # Physical 1920,0 1920x1020 on a monitor at 1920,0 with 125 %: Qt keeps the corner, scales the inside.
    assert to_logical((1920, 0, 1920, 1020), (1920, 0), 1.25) == (1920, 0, 1536, 816)
    assert to_logical((2170, 100, 500, 400), (1920, 0), 1.25) == (2120, 80, 400, 320)
    assert to_logical((300, 150, 600, 450), (0, 0), 1.5) == (200, 100, 400, 300)


def test_a_replica_fills_its_window_on_a_scaled_display(monkeypatch):
    widget = WindowReplicaWidget(1)
    monkeypatch.setattr(widget, "devicePixelRatioF", lambda: 1.5)
    seen = []
    monkeypatch.setattr(widget.thumbnail, "update", lambda width, height, **_rest: seen.append((width, height)))
    monkeypatch.setattr(widget.thumbnail, "source_size", lambda: (0, 0))
    widget.resize(200, 100)
    widget._refresh()
    assert seen[-1] == (300, 150)
    widget.close()


def test_a_pinned_capture_has_the_size_it_had_on_screen():
    pixmap = QPixmap(600, 450)
    pixmap.setDevicePixelRatio(1.5)
    widget = PinnedImageWidget(pixmap)
    assert widget.base_size() == (400, 300) and (widget.width(), widget.height()) == (400, 300)
    widget.close()


def test_click_ripples_land_under_the_cursor(make_main_window, monkeypatch):
    from frontengine.ui.page.presentation import presentation_setting_ui as module
    page = make_main_window().presentation_setting_ui

    class Cursor:
        @staticmethod
        def pos():
            return QPoint(1000, 600)
    monkeypatch.setattr(module, "QCursor", Cursor)
    points = []

    class Layer(QWidget):
        def add_ripple(self, point):
            points.append(point)
    layer = Layer()
    layer.move(100, 50)
    page.cursor_widget_list.append(layer)
    page._on_mouse_clicked(1500, 900)                # physical, at 150 %
    page.cursor_widget_list.clear()
    assert points == [QPoint(900, 550)]
    layer.close()


class _Layer(BaseWidget):
    def draw_content(self, painter):
        """Nothing to draw."""


def test_a_layer_over_a_whole_monitor_keeps_to_it():
    user_setting_dict["overlay_geometry"] = {}
    screen = QGuiApplication.primaryScreen().geometry()
    layer = _Layer()
    layer.setGeometry(screen)
    layer.remember_geometry()
    assert user_setting_dict["overlay_geometry"] == {}
    save_overlay_geometry("_Layer", 10, 10, 50, 50)
    layer.restore_saved_geometry()
    assert layer.geometry() == screen
    small = _Layer()
    small.setGeometry(1, 1, 30, 30)
    small.restore_saved_geometry()
    assert small.geometry() == QRect(10, 10, 50, 50)
    save_overlay_geometry("_Layer", -9000, -9000, 50, 50)
    small.restore_saved_geometry()
    assert small.geometry() == QRect(10, 10, 50, 50)
    user_setting_dict["overlay_geometry"] = {}
    layer.close()
    small.close()


def test_a_region_is_grabbed_without_its_own_outline():
    from frontengine.show.capture.region_capture import RegionCaptureWidget
    widget = RegionCaptureWidget()
    widget.resize(400, 300)
    widget.begin(QPoint(100, 100))
    widget.extend(QPoint(199, 150))
    rect = widget.selection()
    image = widget._raster_content()
    assert all(image.pixelColor(x, y).alpha() == 0 for x in (rect.left(), rect.right())
               for y in (rect.top(), rect.bottom()))
    assert image.pixelColor(rect.left() - 2, rect.center().y()).alpha() == 255
    widget.close()


def test_reminders_of_one_name_each_have_their_own_time():
    now = [datetime(2026, 11, 26, 8, 0)]
    entries = [{"label": "Drink", "kind": "at", "at": "09:00"}, {"label": "Drink", "kind": "at", "at": "15:00"},
               {"label": "Off", "kind": "at", "at": "10:00", "enabled": False}]
    tracker = ReminderTracker(lambda: entries, lambda: now[0])
    heard = []
    while now[0].hour < 20:
        heard += [(label, now[0].hour) for label in tracker.tick()]
        now[0] += timedelta(minutes=10)
        if now[0].hour == 12:
            entries[2]["enabled"] = True                # after its time: nothing to make up for
    assert heard == [("Drink", 9), ("Drink", 15)]


def test_a_clock_turned_back_is_not_midnight():
    now = [datetime(2026, 11, 1, 1, 59)]
    service = PresetScheduleService(lambda: {"enabled": True, "preset": "p", "hour": 9, "minute": 0}, lambda: now[0])
    fired = []
    service.preset_due.connect(fired.append)
    for moment in (now[0], datetime(2026, 11, 1, 1, 0), datetime(2026, 11, 1, 8, 59), datetime(2026, 11, 1, 9, 0),
                   datetime(2026, 11, 1, 23, 59), datetime(2026, 11, 2, 0, 1), datetime(2026, 11, 2, 9, 30)):
        now[0] = moment
        service.poll_once()
    assert fired == ["p", "p"]


def test_weather_is_asked_for_right_after_boot_and_for_the_place_asked_about(monkeypatch):
    clock = [120.0]                                     # two minutes after the computer started
    monkeypatch.setattr(weather_service.time, "monotonic", lambda: clock[0])
    service = WeatherService()
    asked = []
    monkeypatch.setattr(service, "refresh_async", lambda: asked.append(clock[0]))
    service.current()
    assert asked == [120.0]

    def forecast(_url, opener=None):
        service.set_location(1.0, 2.0)                  # the user picks another city meanwhile
        return {"answer": True}
    monkeypatch.setattr(weather_service, "fetch_json", forecast)
    monkeypatch.setattr(weather_service, "parse_forecast", lambda _payload: {"temperature": 20})
    assert service.refresh() == {}
    monkeypatch.setattr(weather_service, "fetch_json", lambda _url, opener=None: {"answer": True})
    assert service.refresh() == {"temperature": 20}


def test_notes_put_away_come_back_and_unused_ones_are_left_alone(make_main_window):
    window = make_main_window({"sticky_notes": [{"text": "stored"}]})
    page = window.widgets_setting_ui
    page.save_notes()
    assert user_setting_dict["sticky_notes"] == [{"text": "stored"}]
    page.add_note("buy milk")
    page.close_notes()
    page.save_notes()
    assert [entry["text"] for entry in user_setting_dict["sticky_notes"]] == ["buy milk"]
    page.add_note("second")
    window.control_center_ui.clear_all()
    page.save_notes()
    assert [entry["text"] for entry in user_setting_dict["sticky_notes"]] == ["buy milk", "second"]


def test_close_all_stops_the_sound_capture_and_the_stop_buttons(make_main_window, monkeypatch):
    window = make_main_window()
    page = window.widgets_setting_ui
    stopped = []
    monkeypatch.setattr(page.capture, "start", lambda *_args: True)
    monkeypatch.setattr(page.capture, "stop", lambda *_args: stopped.append(True))
    started = page.spectrum_button.text()
    page.start_spectrum()
    assert page.spectrum_button.text() != started
    window.screen_care_setting_ui.start_filter()
    window.control_center_ui.clear_all()
    assert stopped and page.spectrum_button.text() == started
    assert window.screen_care_setting_ui.filter_widget_list == []


def test_a_frozen_screen_and_replicas_are_within_reach(make_main_window):
    window = make_main_window()
    frozen, replica = QWidget(), QWidget()
    window.presentation_setting_ui.freeze_widget_list.append(frozen)
    window.tools_setting_ui.replica_widget_list.append(replica)
    assert {frozen, replica} <= set(window.control_center_ui.all_overlays())
    window.control_center_ui.clear_all()
    assert window.tools_setting_ui.replica_widget_list == []
