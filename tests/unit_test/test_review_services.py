"""Platform services, pages and dialogs: what the whole-project review found."""
import contextlib
import socket
import sys
import threading
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QObject, QRect, Qt, Signal
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPixmap
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QMessageBox, QTableWidgetItem, QWidget

from frontengine.ui.dialog.dialog_kit import save_or_tell
from frontengine.user_setting.user_setting_file import user_setting_dict
from frontengine.utils.audio_meter.system_audio_meter import REOPEN_SECONDS, ReopeningMeter
from frontengine.utils.clipboard.clipboard_history import ClipboardHistory
from frontengine.utils.input_watch import input_watch_service as input_watch
from frontengine.utils.keep_awake import keep_awake
from frontengine.utils.macos.input import _LETTER_CODES
from frontengine.utils.now_playing.now_playing import BackgroundNowPlaying
from frontengine.utils.recording.frame_recorder import composite_inset
from frontengine.utils.redirect_manager.redirect_manager_class import redirect_manager_instance
from frontengine.utils.remote.remote_server import _TLSHTTPServer
from frontengine.utils.screen_text.local_ocr import TesseractOcr
from frontengine.utils.system_stats.system_stats import SystemStats, network_delta
from frontengine.utils.virtual_desktop.virtual_desktop import DesktopVisibility
from frontengine.utils.web_url import normalize_web_url
from frontengine.utils.window_pin.topology_profiles import unique_overlays


# ----- platform services ------------------------------------------------------------------------

def test_a_layer_over_a_whole_monitor_is_not_a_misplaced_window():
    layer, note = QWidget(), QWidget()
    layer.setGeometry(QGuiApplication.primaryScreen().geometry())
    note.setGeometry(5, 5, 60, 40)
    found = [widget for _key, widget in unique_overlays(lambda: [[layer, note]], unique_only=False)]
    assert found == [note]
    layer.close()
    note.close()


def test_network_totals_never_run_backwards():
    before = {"a": (100, 10), "vpn": (5_000_000_000, 7)}
    assert network_delta(before, {"a": (160, 30)}) == (60, 20)                         # an adapter went away
    assert network_delta(before, {"a": (160, 30), "vpn": (3, 1)}) == (60, 20)          # and started over
    assert network_delta(before, {"new": (999, 999)}) == (0, 0)


@pytest.mark.skipif(sys.platform != "win32", reason="GetIfTable2")
def test_the_interface_row_has_the_size_windows_says_and_rates_are_sane():
    import ctypes
    from frontengine.utils.system_stats.system_stats import _interface_row
    assert ctypes.sizeof(_interface_row()) == 1352
    stats = SystemStats()
    stats.network()
    QTest.qWait(50)
    assert all(rate is None or 0 <= rate < 10 ** 12 for rate in stats.network())


def test_the_camera_inset_is_whole_at_any_scaling():
    sizes = []
    for ratio in (1.0, 1.5):
        base = QPixmap(1200, 900)
        base.fill(QColor("black"))
        base.setDevicePixelRatio(ratio)
        inset = QPixmap(200, 150)
        inset.fill(QColor("red"))
        image = composite_inset(base, inset).toImage()
        assert (image.width(), image.height()) == (1200, 900)
        sizes.append(sum(image.pixelColor(x, y) == QColor("red") for x in range(0, 1200, 5) for y in range(0, 900, 5)))
    assert sizes[0] == sizes[1] > 100


def test_a_silent_meter_is_opened_on_the_device_there_is_now():
    clock, opened = [0.0], []

    class Meter:
        def __init__(self, value):
            self.value, self.closed = value, False

        def level(self):
            return self.value

        def close(self):
            self.closed = True
    devices = [None, 0.0, 0.5]

    def factory():
        opened.append(Meter(devices[min(len(opened), 2)]))
        return opened[-1]
    meter = ReopeningMeter(factory, lambda: clock[0])
    assert meter.level() is None
    clock[0] = REOPEN_SECONDS - 1
    assert meter.level() is None and len(opened) == 1
    clock[0] = REOPEN_SECONDS
    assert meter.level() == 0.0 and opened[0].closed
    clock[0] = 2 * REOPEN_SECONDS
    assert meter.level() == 0.5
    clock[0] = 9 * REOPEN_SECONDS
    assert meter.level() == 0.5 and len(opened) == 3          # playing: left alone


@pytest.mark.skipif(sys.platform != "win32", reason="SO_EXCLUSIVEADDRUSE")
def test_the_remotes_port_is_not_shared():
    first = _TLSHTTPServer(("127.0.0.1", 0), None)
    try:
        port = first.server_address[1]
        other = socket.socket()
        other.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        with pytest.raises(OSError):
            other.bind(("127.0.0.1", port))
        other.close()
        with pytest.raises(OSError):
            _TLSHTTPServer(("127.0.0.1", port), None)
    finally:
        first.server_close()


def test_programs_are_run_from_fixed_places_only(tmp_path, monkeypatch):
    planted = tmp_path / ("tesseract.exe" if sys.platform == "win32" else "tesseract")
    planted.write_bytes(b"x")
    planted.chmod(0o755)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PATH", str(tmp_path))
    assert TesseractOcr().executable != str(planted)
    assert all(command[0].startswith("/") for command in keep_awake._HELPERS.values())
    assert "/usr/bin/sleep" in keep_awake._HELPERS["linux"]


def test_an_overlay_hidden_by_hand_is_not_brought_back_with_the_desktop():
    class Overlay:
        def __init__(self, handle, shown):
            self.handle, self.shown = handle, shown

        def winId(self):
            return self.handle

        def isVisible(self):
            return self.shown
    hidden, shown = Overlay(1, False), Overlay(2, True)
    visibility = DesktopVisibility()
    assert visibility.decide([hidden, shown], lambda _handle: False)["hide"] == [shown]
    assert visibility.decide([hidden, shown], lambda _handle: True)["show"] == [shown]


def test_ctrl_combinations_name_their_key_and_lost_modifiers_are_let_go():
    assert input_watch.key_name(SimpleNamespace(char="\x13", vk=0x53)) == "s"
    assert input_watch.key_name(SimpleNamespace(char="\t", vk=0x49)) == "i"
    assert input_watch.key_name(SimpleNamespace(char="\x01")) == "a"
    assert input_watch.key_name(SimpleNamespace(char="é", vk=1)) == "é"
    service = input_watch.InputWatchService()
    heard = []
    service.key_pressed.connect(heard.append)
    service._on_press(SimpleNamespace(char=None, name="cmd"))
    service._still_down = lambda name: name != "cmd"
    service._on_press(SimpleNamespace(char="x", vk=0x58))
    assert heard == [["x"]]


def test_asking_what_plays_never_waits_for_the_player():
    release, asked = threading.Event(), []

    def slow():
        asked.append(True)
        release.wait(5)
        return "Song"
    provider = BackgroundNowPlaying(slow)
    assert provider() is None and provider() is None
    release.set()
    for _try in range(200):
        if provider._value == "Song":
            break
        QTest.qWait(10)
    assert provider._value == "Song" and len(asked) == 1


def test_pinned_phrases_past_the_limit_survive_loading():
    history = ClipboardHistory(limit=5)
    history.load([{"text": f"pinned {n}", "pinned": True} for n in range(8)]
                 + [{"text": f"plain {n}", "pinned": False} for n in range(8)])
    texts = [entry["text"] for entry in history.entries]
    assert all(f"pinned {n}" in texts for n in range(8))


def test_mac_letters_have_their_own_key_codes():
    assert [_LETTER_CODES[letter] for letter in "AQBLNM"] == [0, 12, 11, 37, 45, 46]
    assert _LETTER_CODES["."] == 47


def test_redirecting_twice_adds_no_second_set_of_handlers(monkeypatch):
    import logging
    monkeypatch.setattr(sys, "stdout", sys.stdout)
    monkeypatch.setattr(sys, "stderr", sys.stderr)
    logger = logging.getLogger("FrontEngine_RedirectManager")
    redirect_manager_instance.set_redirect()
    count = len(logger.handlers)
    redirect_manager_instance.set_redirect()
    assert len(logger.handlers) == count


# ----- dialogs ----------------------------------------------------------------------------------

def test_the_comparison_and_the_version_windows_can_be_closed(make_main_window):
    from frontengine.ui.dialog.image_compare_dialog import ImageCompareDialog
    from frontengine.ui.dialog.preset_versions_dialog import PresetVersionsDialog
    window = make_main_window()
    window.image_setting_ui.open_image_compare()
    dialog = window.image_setting_ui.compare_dialog
    assert isinstance(dialog, ImageCompareDialog) and dialog.isVisible()
    QTest.keyClick(dialog, Qt.Key.Key_Escape)
    assert not dialog.isVisible()
    versions = PresetVersionsDialog.__new__(PresetVersionsDialog)
    super(PresetVersionsDialog, versions).__init__(window)
    versions.cancel_preview = lambda: True
    versions.show()
    versions.close()
    assert not versions.isVisible()


class _Midi:
    def __init__(self):
        self.calls = []

    def stop(self):
        self.calls.append("stop")

    def start(self, device):
        self.calls.append(device)
        return True


def test_learning_a_midi_control_opens_the_device_first(make_main_window, monkeypatch):
    from frontengine.ui.dialog import remote_control_dialog as module
    monkeypatch.setattr(module, "list_devices", lambda: [(0, "First"), (3, "Pad")])
    monkeypatch.setattr(module, "write_user_setting", lambda: None)
    window, midi = make_main_window({"midi_bindings": {}}), _Midi()
    dialog = module.RemoteControlDialog(window, midi=midi)
    dialog.midi_combobox.setCurrentIndex(1)
    dialog.start_learning()
    assert midi.calls == ["stop", 3]
    assert dialog.learn("note:1")
    combo = dialog.table.cellWidget(0, 1)
    assert combo.currentText() != combo.currentData() and "_" not in combo.currentText()
    dialog.accept()
    assert midi.calls[-1] == 3 and user_setting_dict["midi_device"] == 3
    cancelled = module.RemoteControlDialog(window, midi=midi)
    user_setting_dict["midi_bindings"] = {}
    cancelled.start_learning()
    cancelled.reject()
    assert midi.calls[-1] == "stop"


def test_rules_with_unreadable_days_or_times_are_not_saved_as_always(make_main_window):
    from frontengine.ui.dialog.rules_dialog import RulesDialog, parse_days
    window = make_main_window()
    dialog = RulesDialog(window)
    dialog.add_row({"label": "Mine", "enabled": True, "action": "hide_all", "value": "", "when": {"apps": ["code"]}})
    for column, text in ((1, "Freitags"), (2, "9.30"), (3, "25:00")):
        dialog.table.setItem(0, column, QTableWidgetItem(text))
        user_setting_dict["overlay_rules"] = ["untouched"]
        dialog.accept()
        assert user_setting_dict["overlay_rules"] == ["untouched"] and dialog.status.text()
        dialog.table.setItem(0, column, QTableWidgetItem(""))
    assert parse_days("Mon, 2；Sun".replace("；", ";")) == [0, 2, 6]
    dialog.close()


def test_a_reminder_without_a_readable_time_is_not_dropped(make_main_window, monkeypatch):
    from frontengine.ui.dialog.reminder_dialog import ReminderDialog
    told = []
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *arguments: told.append(arguments[-1])))
    user_setting_dict["reminders"] = [{"label": "Tea", "kind": "at", "at": "09:30", "enabled": True}]
    dialog = ReminderDialog(make_main_window({"reminders": user_setting_dict["reminders"]}))
    row_item = dialog.table.item(0, 2) or dialog.table.item(0, 1)
    row_item.setText("9.30")
    dialog.accept()
    assert told and user_setting_dict["reminders"][0]["at"] == "09:30"
    dialog.close()


def test_a_save_that_fails_leaves_the_old_setting_live(make_main_window, monkeypatch):
    told = []
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *arguments: told.append(arguments[-1])))
    window = make_main_window()
    user_setting_dict["app_profiles"] = {"code": "old"}
    user_setting_dict.pop("something_new", None)

    def full():
        raise OSError("disk full")
    assert save_or_tell(window, {"app_profiles": {}, "something_new": 1}, full) is False
    assert user_setting_dict["app_profiles"] == {"code": "old"} and "something_new" not in user_setting_dict
    assert told == ["disk full"]


def test_two_actions_cannot_share_a_hotkey(make_main_window):
    from frontengine.ui.dialog.hotkey_settings_dialog import HotkeySettingsDialog
    dialog = HotkeySettingsDialog(make_main_window())
    first, second = list(dialog._edits)[:2]
    dialog._edits[first].setText("<ctrl>+<alt>+j")
    dialog._edits[second].setText("<ALT>+<ctrl>+J")
    bindings, invalid = dialog.collect_and_validate()
    assert bindings[first] == "<ctrl>+<alt>+j" and invalid == [second]
    dialog.close()


def test_a_scheduled_preset_that_is_gone_is_kept(make_main_window):
    from frontengine.ui.dialog.preset_schedule_dialog import PresetScheduleDialog
    window = make_main_window({"preset_schedule": {"enabled": True, "preset": "Gone", "hour": None, "minute": 5, "days": []}})
    repository = SimpleNamespace(list_presets=lambda: ["Other"])
    dialog = PresetScheduleDialog(window, repository)
    assert dialog.preset_combobox.currentData() == "Gone" and dialog.hour_spinbox.value() == 9
    dialog.close()


def test_file_filters_separate_their_patterns_with_spaces(monkeypatch):
    from frontengine.ui.dialog import choose_file_dialog as module
    asked = {}
    monkeypatch.setattr(module, "choose_file", lambda _ui, file_filter, extensions, **_rest: asked.update({file_filter: extensions}))
    for choose in (module.choose_gif, module.choose_image, module.choose_player_sound, module.choose_video):
        choose(None)
    assert len(asked) == 4
    for text, extensions in asked.items():
        assert ";" not in text and all(f"*{extension}" in text for extension in extensions)


# ----- pages ------------------------------------------------------------------------------------

@pytest.mark.parametrize("typed, opened", [
    ("www.example.com", "https://www.example.com"), ("example.com:8080/a", "https://example.com:8080/a"),
    ("localhost:3000", "http://localhost:3000"), ("192.168.0.2/cam", "http://192.168.0.2/cam"),
    ("https://example.com", "https://example.com"), ("about:blank", "about:blank"),
    ("file:///C:/a.html", "file:///C:/a.html"), ("just words", "just words"), ("word", "word")])
def test_an_address_without_a_scheme_is_completed(typed, opened):
    assert normalize_web_url(typed) == opened


def test_status_labels_follow_the_language(make_main_window):
    from frontengine.utils.multi_language.language_wrapper import language_wrapper
    from frontengine.utils.multi_language.retranslate import retranslator
    window = make_main_window()
    image, tools = window.image_setting_ui, window.tools_setting_ui
    retranslator.set_text(image.ready_label, "Ready")
    tools._set_vcam_status("tools_vcam_sending", "Sending to {device}", device="Cam")
    folder_label = window.wallpaper_setting_ui.folder_label
    window.wallpaper_setting_ui.folders[window.wallpaper_setting_ui.current_monitor()] = "C:/walls"
    window.wallpaper_setting_ui._show_folder_for_monitor()
    ready, sending = image.ready_label.text(), tools.virtual_camera_status.text()
    try:
        language_wrapper.reset_language("Deutsch")
        retranslator.apply()
        assert image.ready_label.text() not in ("", ready)
        assert "Cam" in tools.virtual_camera_status.text() and tools.virtual_camera_status.text() != sending
        assert folder_label.text() == "C:/walls"
    finally:
        language_wrapper.reset_language("English")
        retranslator.apply()


def _picture(path, color):
    image = QImage(8, 8, QImage.Format.Format_RGB32)
    image.fill(QColor(color))
    image.save(str(path))
    return str(path)


def test_a_slideshow_changes_only_its_own_pictures_and_is_remembered(make_main_window, tmp_path, monkeypatch):
    page = make_main_window().image_setting_ui
    folder = tmp_path / "show"
    folder.mkdir()
    first, second = _picture(folder / "1.png", "red"), _picture(folder / "2.png", "blue")
    chosen = _picture(tmp_path / "chosen.png", "green")
    page.slideshow_folder = str(folder)
    page.slideshow_checkbox.setChecked(True)
    page._on_file_dropped(chosen)
    assert str(page.image_widget_list[-1].image_path) == chosen and page.image_path == chosen
    page.start_play_image()
    running = page.image_widget_list[-1]
    assert str(running.image_path) == first and page.image_path == chosen
    page._advance_slideshow()
    assert str(running.image_path) == second and str(page.image_widget_list[0].image_path) == chosen
    page.slideshow_shuffle_checkbox.setChecked(True)
    page.slideshow_interval_combobox.setCurrentText("30")
    state = page.get_state()
    page.slideshow_checkbox.setChecked(False)
    page.slideshow_folder = None
    page.set_state(state)
    assert page.slideshow_checkbox.isChecked() and page.slideshow_folder == str(folder)
    assert page.slideshow_interval_combobox.currentText() == "30"
    for widget in page.image_widget_list[:]:
        widget.close()
    page._slideshow_timer.stop()
    page.image_widget_list.clear()


def test_show_all_leaves_the_other_dashboard_pages_away(make_main_window):
    window = make_main_window()
    page, pages = window.web_setting_ui, [QWidget(), QWidget()]
    page.dashboard_widgets.extend(pages)
    page._apply_dashboard_visibility()
    window.control_center_ui.show_all()
    assert pages[0].isVisible() and not pages[1].isVisible()
    page.show_next_dashboard_page()
    assert pages[1].isVisible() and not pages[0].isVisible()
    for widget in pages:
        widget.close()
    page.dashboard_widgets.clear()


def test_dashboard_addresses_are_never_local_files(make_main_window, monkeypatch):
    from frontengine.ui.page.web import web_setting_ui as module
    page, made = make_main_window().web_setting_ui, []

    class Web(QWidget):
        def __init__(self, url, is_file=False):
            super().__init__()
            made.append((url, is_file))

        def __getattr__(self, name):
            if name.startswith("set_"):
                return lambda *_arguments, **_named: None
            raise AttributeError(name)
    monkeypatch.setattr(module, "WebWidget", Web)
    page.open_file = True
    page.dashboard_edit.setPlainText("example.com")
    page.start_dashboard()
    assert made == [("https://example.com", False)]
    page.close_dashboard()


def test_cameras_can_be_listed_again_and_the_choice_is_kept(make_main_window, monkeypatch):
    from frontengine.ui.page.tools import tools_setting_ui as module
    page = make_main_window().tools_setting_ui
    monkeypatch.setattr(module, "list_cameras", lambda: [("a", "A"), ("b", "B")])
    page.reload_cameras()
    page.camera_device_combobox.setCurrentIndex(1)
    monkeypatch.setattr(module, "list_cameras", lambda: [("c", "C"), ("a", "A"), ("b", "B")])
    page.camera_refresh_button.click()
    assert page.camera_device_combobox.count() == 3 and page.camera_device_combobox.currentData() == "b"


def test_closing_the_whiteboard_on_itself_resets_its_button(make_main_window):
    page = make_main_window().presentation_setting_ui
    start = page.whiteboard_button.text()
    page.start_whiteboard()
    board = page.whiteboard_widget_list[0]
    assert page.whiteboard_button.text() != start
    board.close()
    for _try in range(100):
        if page.whiteboard_button.text() == start:
            break
        QTest.qWait(10)
    assert page.whiteboard_button.text() == start and page.whiteboard_widget_list == []


def test_an_overlay_bound_anew_while_its_old_target_hid_it_comes_back():
    from frontengine.utils.window_pin.follow_window import WindowFollowService

    class Backend:
        minimized = False

        def bind(self, handle):
            return {"handle": handle}

        def snapshot(self, _identity):
            return {"rect": (0, 0, 100, 100), "minimized": self.minimized}

        def geometry(self, widget):
            return (widget.x(), widget.y(), widget.width(), widget.height())

        def release(self, _identity):
            """Nothing held."""

        def move(self, *_arguments, **_named):
            """Stays."""
    service = WindowFollowService(backend=Backend())
    widget = QWidget()
    widget.setGeometry(QRect(0, 0, 10, 10))
    widget.show()
    service.bind(widget, 111111)
    binding = service.bindings[id(widget)]
    binding.hidden_by_target = True
    binding.changing_visibility = True
    widget.hide()
    binding.changing_visibility = False
    service.bind(widget, 222222)
    again = service.bindings[id(widget)]
    assert again.desired_visible and again.hidden_by_target
    service.unbind(widget)
    assert widget.isVisible()
    widget.close()


class _FakeClipboard(QObject):
    """Stands in for the system clipboard, so the test never reads what the developer copied."""
    dataChanged = Signal()

    def __init__(self):
        super().__init__()
        self.value = ""

    def text(self):
        return self.value


def _refuse_saving(monkeypatch):
    from frontengine.ui import main_ui

    told = []

    def refuse():
        raise OSError("disk full")
    monkeypatch.setattr(main_ui, "write_user_setting", refuse)
    monkeypatch.setattr(main_ui, "show_toast", lambda message, *rest, **named: told.append(message))
    return told


def test_turning_clipboard_recording_off_stops_it_even_if_the_save_fails(make_main_window, monkeypatch):
    from frontengine.utils.clipboard import clipboard_watcher as watcher_module

    fake = _FakeClipboard()
    monkeypatch.setattr(watcher_module, "QGuiApplication", SimpleNamespace(clipboard=lambda: fake))
    window = make_main_window()
    window.set_clipboard_history(True)
    fake.value = "kept"
    fake.dataChanged.emit()
    recorded = len(window.clipboard_history.to_list())
    told = _refuse_saving(monkeypatch)
    try:
        with contextlib.suppress(OSError):
            window.set_clipboard_history(False)
        fake.value = "copied after turning it off"
        fake.dataChanged.emit()
        assert len(window.clipboard_history.to_list()) == recorded == 1
        assert window.clipboard_watcher.running is False
        assert user_setting_dict["clipboard_history"] is False
        assert told and "next launch" in told[0]
    finally:
        window.clipboard_watcher.stop()


def test_turning_usage_tracking_off_stops_it_even_if_the_save_fails(make_main_window, monkeypatch):
    window = make_main_window()
    window.usage_service.start()
    told = _refuse_saving(monkeypatch)
    try:
        with contextlib.suppress(OSError):
            window.set_usage_tracking(False)
        assert window.usage_service.running is False
        assert told and "next launch" in told[0]
    finally:
        window.usage_service.stop()


def test_a_slideshow_folder_alone_is_enough_for_the_screensaver(make_main_window, tmp_path, monkeypatch):
    window = make_main_window()
    page = window.image_setting_ui
    folder = tmp_path / "show"
    folder.mkdir()
    first = _picture(folder / "1.png", "red")
    page.slideshow_folder = str(folder)
    page.slideshow_checkbox.setChecked(True)
    shown, asked = [], []
    monkeypatch.setattr(page, "_show", lambda path, slideshow=False: shown.append((path, slideshow)))
    monkeypatch.setattr(page, "choose_and_copy_file_to_cwd_image_dir_then_play", lambda: asked.append(True))
    assert page.ready_to_play is False
    window._start_screensaver("image")
    page._slideshow_timer.stop()
    assert shown == [(first, True)] and asked == []


def test_an_empty_slideshow_folder_leaves_the_screensaver_idle(make_main_window, tmp_path, monkeypatch):
    window = make_main_window()
    page = window.image_setting_ui
    folder = tmp_path / "empty"
    folder.mkdir()
    page.slideshow_folder = str(folder)
    page.slideshow_checkbox.setChecked(True)
    started = []
    monkeypatch.setattr(page, "start_play_image", lambda: started.append(True))
    assert page.has_playable_source() is False
    window._start_screensaver("image")
    assert started == []
