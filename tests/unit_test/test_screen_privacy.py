"""
螢幕分享隱私的純邏輯測試：什麼算「正在分享」、遮蔽層為什麼不能被藏起來。

Pure-logic tests for screen-sharing privacy: what counts as sharing, and why a
masking overlay must not be hidden along with the rest.
"""
from frontengine.utils.screen_privacy.capture_affinity import (
    WDA_EXCLUDEFROMCAPTURE, WDA_NONE, available, apply_to_widget, apply_to_widgets,
    is_excluded_from_capture, set_excluded_from_capture,
)
from frontengine.utils.screen_privacy.share_watch import (
    DEFAULT_SHARING_APPS, ShareWatchService, running_app_names, sharing_app_running,
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


def test_window_names_are_normalized_and_deduplicated() -> None:
    names = running_app_names(lambda: [(1, "Zoom Meeting"), (2, "Zoom Meeting"), (3, "Code")])
    assert names == ["zoom meeting", "code"]


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
