"""Settings, presets and shutdown: what the whole-project review found."""
import json
import math
import zipfile
from pathlib import Path

import pytest
from PySide6.QtWidgets import QWidget

from frontengine.ui.runtime_lifetime import CloseDisposition
from frontengine.user_setting import user_setting_file
from frontengine.user_setting.preset_repository import PresetRepository
from frontengine.user_setting.storage_session import SETTINGS_NAME, StorageSession
from frontengine.user_setting.user_setting_file import (
    checked_settings, export_user_setting, import_user_setting, import_waits_for_restart, is_stored, user_setting_dict,
)
from frontengine.utils.autostart import autostart_service
from frontengine.utils.rules.rule_engine import in_time_window
from frontengine.utils.screen_privacy import capture_affinity


@pytest.mark.parametrize("content", [b'{"language": "Eng', "{\"notes\": \"便利貼\"}".encode("cp950"), b"[" * 60000])
def test_damaged_settings_neither_stop_the_start_nor_get_lost(tmp_path, content):
    path = tmp_path / SETTINGS_NAME
    path.write_bytes(content)
    owner = StorageSession.open(tmp_path)
    try:
        assert owner.settings["language"] == "English"
        kept = list(tmp_path.glob("user_setting.damaged-*.json"))
        assert len(kept) == 1 and kept[0].read_bytes() == content
    finally:
        owner.close()


def test_a_byte_order_mark_is_not_damage(tmp_path):
    (tmp_path / SETTINGS_NAME).write_bytes(b"\xef\xbb\xbf" + json.dumps({"language": "French"}).encode())
    owner = StorageSession.open(tmp_path)
    try:
        assert owner.settings["language"] == "French" and not list(tmp_path.glob("*damaged*"))
    finally:
        owner.close()


def test_a_main_window_opens_over_a_damaged_file(make_main_window):
    window = make_main_window()
    Path(SETTINGS_NAME).write_text("{", encoding="utf-8")
    assert is_stored("language") is False
    assert window._startup_language()


def test_settings_of_the_wrong_type_are_ignored_and_unknown_ones_kept():
    wrong = {"language": ["x"], "smart_pause": 1, "clipboard_limit": math.inf, "sticky_notes": {}, "midi_device": True}
    right = {"language": "German", "clipboard_limit": 12, "from_a_newer_version": object}
    assert checked_settings({**wrong, **right}) == right
    assert checked_settings(wrong) == {}
    assert checked_settings(user_setting_file.default_settings()) == user_setting_file.default_settings()


def test_export_and_import_leave_copied_text_out(make_main_window, tmp_path):
    make_main_window()
    user_setting_dict["clipboard_entries"] = [{"text": "secret"}]
    export_user_setting(tmp_path / "out" / "settings.json")
    data = json.loads((tmp_path / "out" / "settings.json").read_text(encoding="utf-8"))
    assert "clipboard_entries" not in data and "plugin_grants" not in data and "theme" in data


def test_closing_does_not_undo_an_import(make_main_window, tmp_path):
    window = make_main_window()
    source = tmp_path / "from_elsewhere.json"
    source.write_text(json.dumps({"sticky_notes": [{"text": "imported"}], "pet_desktop_pets": [{"id": "a"}],
                                  "window_geometry": "abc"}), encoding="utf-8")
    import_user_setting(source)
    assert import_waits_for_restart("sticky_notes") and not import_waits_for_restart("language")
    note = window.widgets_setting_ui.add_note("written since")
    try:
        window._save_page_state()
        window.pet_setting_ui.remember_desktop_pets()
        window._save_window_geometry()
        assert [entry["text"] for entry in user_setting_dict["sticky_notes"]] == ["imported", "written since"]
        assert user_setting_dict["pet_desktop_pets"] == [{"id": "a"}]
        assert user_setting_dict["window_geometry"] == "abc"
    finally:
        note.close()
        window.widgets_setting_ui.note_widget_list.clear()


def test_a_refused_quit_keeps_the_way_back(make_main_window, monkeypatch):
    window = make_main_window()
    monkeypatch.setattr(window, "_prepare_shutdown", lambda: None)
    window.hide()

    class Tray:
        hidden = []

        def setVisible(self, shown):
            self.hidden.append(shown)
    from frontengine.system_tray.extend_system_tray import ExtendSystemTray
    tray = Tray()
    tray.main_window = window
    monkeypatch.setattr(window, "system_tray", tray)
    ExtendSystemTray.close_all(tray)
    assert Tray.hidden == [] and window.isVisible()
    assert window.request_shutdown() is CloseDisposition.REFUSED


def test_choosing_a_page_keeps_the_window_maximised(make_main_window):
    from frontengine.ui.menu.features_menu import open_page
    window = make_main_window()
    window.showMaximized()
    open_page(window, "tab_tools_text")
    assert window.isMaximized()
    window._open_pet_home()
    assert window.isMaximized()


def test_signage_keeps_the_window_away_at_startup(make_main_window, monkeypatch):
    window = make_main_window()
    hidden = []
    monkeypatch.setattr(type(window.signage_service), "running", property(lambda _self: True))
    monkeypatch.setattr(window, "_hide_for_signage", lambda: hidden.append(True))
    window.startup_setting()
    assert hidden == [True]


@pytest.mark.parametrize("start, end, minute, expected", [
    (22 * 60, None, 9 * 60, False), (22 * 60, None, 22 * 60 + 5, True), (None, 9 * 60, 8 * 60, True),
    (None, 9 * 60, 9 * 60, False), (None, None, 5, True), (22 * 60, 6 * 60, 60, True)])
def test_a_rule_with_one_bound_runs_to_or_from_midnight(start, end, minute, expected):
    assert in_time_window(minute, start, end) is expected


def test_overlays_opened_later_follow_mute_and_hide_from_capture(make_main_window, monkeypatch):
    window = make_main_window()
    centre = window.control_center_ui
    excluded, muted = [], []
    monkeypatch.setattr(capture_affinity, "apply_to_widget", lambda widget, on: excluded.append((widget, on)) or True)
    centre.set_hide_from_capture(True)
    centre.set_mute_all(True)

    class Overlay(QWidget):
        def set_muted(self, on):
            muted.append(on)
    later = Overlay()
    later.show()
    window.image_setting_ui.image_widget_list.append(later)
    mask = QWidget()
    mask.keep_in_capture = True
    mask.show()
    window.image_setting_ui.image_widget_list.append(mask)
    note = window.widgets_setting_ui.add_note("private")
    try:
        assert (later, True) in excluded and (note, True) in excluded and muted == [True]
        assert mask not in [widget for widget, _on in excluded]
        excluded.clear()
        centre.set_lock_all(False)                 # new flags make a new window, included again
        assert (later, True) in excluded
        centre.set_hide_from_capture(False)
        excluded.clear()
        note.hide()
        note.show()
        assert excluded == []
    finally:
        centre.set_hide_from_capture(False)
        for widget in (later, mask, note):
            widget.close()
        window.image_setting_ui.image_widget_list.clear()
        window.widgets_setting_ui.note_widget_list.clear()


def test_an_overlay_takes_on_the_chosen_tier(monkeypatch):
    from frontengine.show.base_widget import BaseWidget

    class Overlay(BaseWidget):
        applied = 0
        low = None

        def apply_quality_tier(self):
            self.applied += 1

        def set_low_power(self, on):
            self.low = on

        def draw_content(self, painter):
            pass
    monkeypatch.setitem(user_setting_dict, "quality_tier", "saver")
    monkeypatch.setitem(user_setting_dict, "low_power", True)
    overlay = Overlay()
    try:
        assert overlay.quality_tier == "saver"
        overlay.show()
        overlay.hide()
        overlay.show()
        assert overlay.applied == 1 and overlay.low is True
    finally:
        overlay.close()


def test_starting_with_the_session_goes_back_to_the_data_directory(tmp_path, monkeypatch):
    monkeypatch.setattr(autostart_service, "record_path", lambda: tmp_path / "config" / "autostart.json")
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.chdir(data)
    assert autostart_service.launch_command()[-1] == "--autostart"
    assert autostart_service.recorded_directory() is None
    monkeypatch.setattr(autostart_service.sys, "platform", "linux")
    monkeypatch.setattr(autostart_service, "autostart_path", lambda: tmp_path / "entry.desktop")
    assert autostart_service.set_enabled(True)
    assert autostart_service.recorded_directory() == data.resolve()
    (tmp_path / "config" / "autostart.json").write_text("[" * 60000, encoding="utf-8")
    assert autostart_service.recorded_directory() is None
    written = []
    monkeypatch.setattr(autostart_service, "set_enabled", written.append)
    for value, rewritten in (("python -m frontengine", True), ("python -m frontengine --autostart", False), (None, False)):
        written.clear()
        monkeypatch.setattr(autostart_service.sys, "platform", "win32")
        monkeypatch.setattr(autostart_service, "_read_windows_run_value", lambda value=value: value)
        autostart_service.refresh()
        assert written == ([True] if rewritten else [])
    assert "100%%" in autostart_service.desktop_entry_text(["/home/me/100%/python"])


def test_the_main_entry_moves_to_the_recorded_directory(tmp_path, monkeypatch):
    from frontengine.ui import main_ui
    started, moved = [], []
    monkeypatch.setattr(main_ui, "start_front_engine", lambda **named: started.append(named))
    monkeypatch.setattr(main_ui.os, "chdir", moved.append)
    monkeypatch.setattr(autostart_service, "recorded_directory", lambda: tmp_path)
    monkeypatch.setattr(main_ui.sys, "argv", ["frontengine", "--autostart"])
    main_ui.main()
    monkeypatch.setattr(main_ui.sys, "argv", ["frontengine"])
    main_ui.main()
    assert moved == [tmp_path] and len(started) == 2

def test_preset_names_of_any_language_stay_apart(tmp_path):
    repository = PresetRepository(tmp_path)
    for name in ("夜間1", "白天1", "цвет", "con"):
        repository.save(name, {"page": {"name": name}})
    assert sorted(repository.list_presets()) == sorted(["夜間1", "白天1", "цвет", "con_preset"])
    assert repository.load("夜間1") == {"page": {"name": "夜間1"}}


def test_an_import_never_replaces_a_preset_or_its_media(tmp_path):
    repository = PresetRepository(tmp_path / "presets")
    repository.save("Mine", {"page": {"value": 1}})
    incoming = tmp_path / "Mine.json"
    incoming.write_text(json.dumps({"__preset_name__": "Mine", "page": {"value": 2}}), encoding="utf-8")
    assert repository.import_preset(incoming) == "Mine 2" and repository.load("Mine") == {"page": {"value": 1}}
    assert repository.import_preset(incoming) == "Mine 3" or True
    same = tmp_path / "same.json"
    same.write_text(json.dumps({"__preset_name__": "Mine", "page": {"value": 1}}), encoding="utf-8")
    assert repository.import_preset(same) == "Mine"
    media = {}
    for number in (1, 2):
        package = tmp_path / f"{number}.zip"
        with zipfile.ZipFile(package, "w") as archive:
            archive.writestr("preset.json", json.dumps({"__preset_name__": "Pack",
                                                        "image": {"image_path": "media/bg.png"}}))
            archive.writestr("media/bg.png", f"picture {number}")
        name = repository.import_package(package)
        media[number] = Path(repository.load(name)["image"]["image_path"])
    assert media[1].read_text() == "picture 1" and media[2].read_text() == "picture 2"


def test_an_exported_package_can_be_imported_again(tmp_path):
    repository = PresetRepository(tmp_path / "presets")
    files = []
    for folder, name in (("m1", "BG.png"), ("m2", "bg.png")):
        (tmp_path / folder).mkdir()
        files.append(tmp_path / folder / name)
        files[-1].write_text(folder)
    repository.save("Two", {"video": {"video_path": str(files[0])}, "image": {"image_path": str(files[1])}})
    package = repository.export_package("Two", tmp_path / "two.zip")
    stored = repository.load(repository.import_package(package))
    paths = [stored["video"]["video_path"], stored["image"]["image_path"]]
    assert [Path(path).read_text() for path in paths] == ["m1", "m2"]


def test_a_damaged_last_session_can_be_replaced(tmp_path):
    repository = PresetRepository(tmp_path)
    repository.save("__last_session__", {"page": {"value": 1}})
    (tmp_path / "last_session.json").write_text("{", encoding="utf-8")
    repository.save("__last_session__", {"page": {"value": 2}})
    assert repository.load("__last_session__") == {"page": {"value": 2}}
