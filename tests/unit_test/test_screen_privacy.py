"""
螢幕分享隱私的純邏輯測試：什麼算「正在分享」、遮蔽層為什麼不能被藏起來。

Pure-logic tests for screen-sharing privacy: what counts as sharing, and why a
masking overlay must not be hidden along with the rest.
"""
import pytest

from frontengine.utils.screen_privacy.capture_affinity import (
    WDA_EXCLUDEFROMCAPTURE, WDA_NONE, available, apply_to_widget, apply_to_widgets,
    is_excluded_from_capture, set_excluded_from_capture,
)
from frontengine.utils.screen_privacy.share_watch import (
    DEFAULT_SHARING_APPS, ShareWatchService, sharing_app_running,
)


# --- what counts as sharing -----------------------------------------------
def test_a_watched_app_is_found_by_its_window_title() -> None:
    assert sharing_app_running("zoom", ["Zoom Meeting", "Code"]) == "zoom"


def test_matching_is_case_insensitive() -> None:
    assert sharing_app_running("TEAMS", ["Microsoft Teams"]) == "teams"


def test_an_unrelated_desktop_is_not_sharing() -> None:
    assert sharing_app_running("zoom", ["Code", "Explorer"]) is None


def test_no_windows_at_all_is_not_sharing() -> None:
    assert sharing_app_running("zoom", []) is None


def test_an_empty_list_falls_back_to_the_usual_suspects() -> None:
    assert sharing_app_running("", ["Zoom Meeting"]) in DEFAULT_SHARING_APPS
    assert sharing_app_running(None, ["Discord"]) in DEFAULT_SHARING_APPS


def test_a_meeting_in_a_browser_tab_is_caught_by_the_title() -> None:
    # 標題比對的用意就在這裡：瀏覽器裡開的會議，執行檔名是 chrome
    assert sharing_app_running("meet", ["Meet - abc-defg-hij - Google Chrome"]) == "meet"


# --- the watcher ----------------------------------------------------------
def watcher(config, windows):
    return ShareWatchService(config_provider=lambda: config["value"],
                             window_provider=lambda: windows["value"])


def test_nothing_is_reported_while_the_feature_is_off() -> None:
    config = {"value": {"enabled": False, "apps": "zoom"}}
    windows = {"value": [(1, "Zoom Meeting")]}
    events = []
    service = watcher(config, windows)
    service.sharing_changed.connect(lambda sharing, match: events.append((sharing, match)))
    service.poll_once()
    assert service.sharing is False and events == []


def test_the_change_is_reported_once_in_each_direction() -> None:
    config = {"value": {"enabled": True, "apps": "zoom"}}
    windows = {"value": [(1, "Code")]}
    events = []
    service = watcher(config, windows)
    service.sharing_changed.connect(lambda sharing, match: events.append((sharing, match)))

    service.poll_once()
    assert events == []

    windows["value"] = [(1, "Code"), (2, "Zoom Meeting")]
    service.poll_once()
    service.poll_once()
    assert events == [(True, "zoom")], "no repeat while it stays open"
    assert service.sharing is True and service.match == "zoom"

    windows["value"] = [(1, "Code")]
    service.poll_once()
    assert events[-1] == (False, "")


def test_turning_the_feature_off_reports_that_sharing_stopped() -> None:
    config = {"value": {"enabled": True, "apps": "zoom"}}
    windows = {"value": [(1, "Zoom Meeting")]}
    events = []
    service = watcher(config, windows)
    service.sharing_changed.connect(lambda sharing, match: events.append((sharing, match)))
    service.poll_once()
    assert events == [(True, "zoom")]
    config["value"] = {"enabled": False}
    service.poll_once()
    assert events[-1] == (False, "")


def test_a_failing_window_source_does_not_change_the_state() -> None:
    def boom():
        raise RuntimeError("no window manager")

    service = ShareWatchService(config_provider=lambda: {"enabled": True, "apps": "zoom"},
                                window_provider=boom)
    service.poll_once()
    assert service.sharing is False


# --- capture affinity -----------------------------------------------------
def test_the_two_affinity_values_are_distinct() -> None:
    assert WDA_NONE != WDA_EXCLUDEFROMCAPTURE


def test_availability_is_a_plain_bool() -> None:
    assert isinstance(available(), bool)


def test_a_missing_handle_is_refused_rather_than_guessed() -> None:
    assert set_excluded_from_capture(0, True) is False
    assert is_excluded_from_capture(0) is None
    assert apply_to_widget(None, True) is False


def test_applying_to_nothing_counts_nothing() -> None:
    assert apply_to_widgets([], True) == 0
    assert apply_to_widgets(None, True) == 0


# --- the mask must stay visible -------------------------------------------
def test_a_mask_declares_that_it_stays_in_the_capture() -> None:
    """
    遮蔽層被藏起來就等於沒遮，所以它必須自己宣告要留在擷取結果裡。
    Hiding a mask would defeat the only thing it does, so it declares that it
    stays in the capture.
    """
    from frontengine.show.focus_shield.focus_shield_widget import DistractionMaskWidget

    mask = DistractionMaskWidget()
    assert mask.keep_in_capture is True
    mask.close()


def test_an_ordinary_overlay_does_not_ask_to_stay() -> None:
    from frontengine.show.toast.toast_widget import ToastWidget

    toast = ToastWidget("hello")
    assert toast.keep_in_capture is False
    toast.close()


# --- the capture policy behind the control center -------------------------
def _fake_affinity(monkeypatch, refuse=(), supported=True):
    """Record what each overlay was told; the overlays in ``refuse`` never take it."""
    from frontengine.utils.screen_privacy import capture_affinity

    told = {}

    def apply(widget, excluded):
        if any(widget is refused for refused in refuse) or not supported:
            return False
        told[id(widget)] = excluded
        return True
    monkeypatch.setattr(capture_affinity, "apply_to_widget", apply)
    monkeypatch.setattr(capture_affinity, "available", lambda: supported)
    return told


def _shown_overlay(window):
    from PySide6.QtWidgets import QWidget

    widget = QWidget()
    widget.show()
    window.image_setting_ui.image_widget_list.append(widget)
    return widget


def _tear_down(window, widgets):
    window.control_center_ui.set_auto_hide_from_capture(False)
    window.control_center_ui.set_hide_from_capture(False)
    for widget in widgets:
        widget.close()
    window.image_setting_ui.image_widget_list.clear()


def _toasts(monkeypatch):
    from frontengine.ui import main_ui
    from frontengine.ui.page.control_center import control_center_ui

    shown = []
    monkeypatch.setattr(main_ui, "show_toast", lambda message, *rest, **named: shown.append(message))
    monkeypatch.setattr(control_center_ui, "show_toast", lambda message, *rest, **named: shown.append(message))
    return shown


def test_a_meeting_ending_keeps_the_users_own_hide(make_main_window, monkeypatch) -> None:
    from frontengine.utils.screen_privacy import capture_affinity

    told = _fake_affinity(monkeypatch)
    window = make_main_window()
    _toasts(monkeypatch)
    centre = window.control_center_ui
    existing = _shown_overlay(window)
    later = None
    try:
        centre.set_hide_from_capture(True)
        window._on_sharing_changed(True, "zoom")
        window._on_sharing_changed(False, "")
        assert told[id(existing)] is True
        assert centre.hidden_from_capture and capture_affinity.hidden()
        assert centre.capture_button.text() == "Show in capture"
        later = _shown_overlay(window)
        assert told[id(later)] is True, "an overlay opened after the meeting is still hidden"
        centre.set_hide_from_capture(False)
        assert told[id(existing)] is False and told[id(later)] is False
    finally:
        _tear_down(window, [existing] + ([later] if later else []))


def test_a_meeting_alone_hides_and_then_releases_the_overlays(make_main_window, monkeypatch) -> None:
    told = _fake_affinity(monkeypatch)
    window = make_main_window()
    _toasts(monkeypatch)
    existing = _shown_overlay(window)
    try:
        window._on_sharing_changed(True, "zoom")
        assert told[id(existing)] is True
        assert window.control_center_ui.capture_button.text() == "Hide from capture"
        window._on_sharing_changed(False, "")
        assert told[id(existing)] is False and not window.control_center_ui.hidden_from_capture
    finally:
        _tear_down(window, [existing])


def test_the_capture_report_names_each_outcome() -> None:
    from frontengine.utils.screen_privacy.capture_affinity import CaptureReport

    assert CaptureReport(True, False, 0, 0).outcome == "unsupported"
    assert CaptureReport(True, True, 0, 0).outcome == "none"
    assert CaptureReport(True, True, 2, 0).outcome == "all"
    assert CaptureReport(True, True, 1, 1).outcome == "partial"
    assert CaptureReport(True, True, 0, 2).outcome == "failed"
    assert CaptureReport(True, True, 1, 2).eligible == 3


@pytest.mark.parametrize("open_count, refused, supported, expected", [
    (2, 0, True, "Overlays hidden from screen capture"),
    (2, 1, True, "Only 1 of 2 overlays could be hidden from screen capture"),
    (2, 2, True, "Overlays could not be hidden from screen capture"),
    (0, 0, True, "Screen sharing detected: no overlays are open to hide"),
    (1, 0, False, "Screen sharing detected, but this system cannot hide overlays from capture"),
])
def test_the_sharing_toast_claims_only_what_took_effect(
        make_main_window, monkeypatch, open_count, refused, supported, expected) -> None:
    window = make_main_window()
    overlays = [_shown_overlay(window) for _ in range(open_count)]
    _fake_affinity(monkeypatch, refuse=overlays[:refused], supported=supported)
    shown = _toasts(monkeypatch)
    try:
        window._on_sharing_changed(True, "zoom")
        assert shown == [expected]
    finally:
        _tear_down(window, overlays)


def test_hiding_by_hand_says_so_when_an_overlay_refuses(make_main_window, monkeypatch) -> None:
    window = make_main_window()
    overlays = [_shown_overlay(window), _shown_overlay(window)]
    _fake_affinity(monkeypatch, refuse=overlays[:1])
    shown = _toasts(monkeypatch)
    try:
        window.control_center_ui.toggle_hide_from_capture()
        assert shown == ["Only 1 of 2 overlays could be hidden from screen capture"]
        window.control_center_ui.toggle_hide_from_capture()
        assert len(shown) == 1, "showing them in the capture again needs no warning"
    finally:
        _tear_down(window, overlays)


def test_hiding_by_hand_stays_quiet_when_every_overlay_took_it(make_main_window, monkeypatch) -> None:
    window = make_main_window()
    overlays = [_shown_overlay(window)]
    _fake_affinity(monkeypatch)
    shown = _toasts(monkeypatch)
    try:
        report = window.control_center_ui.set_hide_from_capture(True)
        window.control_center_ui.toggle_hide_from_capture()
        window.control_center_ui.toggle_hide_from_capture()
        assert (report.succeeded, report.failed) == (1, 0) and shown == []
    finally:
        _tear_down(window, overlays)
