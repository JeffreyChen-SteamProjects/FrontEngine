"""
螢幕保護：閒置夠久就放上來，人回來就收掉。

閒置秒數可以注入，所以這裡不必真的等五分鐘也不必去動滑鼠。要釘住的重點是
「只在狀態改變時說話」——每次輪詢都回報「該開了」會把覆蓋層一直重開。

The screensaver: on when idle long enough, off when someone comes back.

The idle seconds are injected, so nothing here waits five minutes or moves a
mouse. The point being pinned down is that it speaks only when the state
changes: answering "should be on" every poll would reopen the overlay forever.
"""
import pytest

from frontengine.utils.screensaver.screensaver_service import (
    DEFAULT_IDLE_MINUTES, MAX_IDLE_MINUTES, MIN_IDLE_MINUTES, SOURCES, ScreensaverState,
    clamp_idle_minutes, normalize_source,
)


class FakeIdle:
    """可以直接設定的閒置秒數。"""

    def __init__(self, seconds=0.0):
        self.seconds = seconds

    def __call__(self):
        return self.seconds


def make_state(idle=0.0, **config):
    settings = {"enabled": True, "idle_minutes": 5, "source": "video"}
    settings.update(config)
    clock = FakeIdle(idle)
    return ScreensaverState(lambda: settings, clock), clock, settings


def test_it_starts_once_the_idle_threshold_is_passed():
    state, clock, _ = make_state(idle=0.0)
    assert state.poll() is None

    clock.seconds = 5 * 60
    assert state.poll() is True
    assert state.active is True


def test_it_says_nothing_while_it_stays_idle():
    """
    這條是重點：持續閒置時只能說一次。每次輪詢都回 True 的話，覆蓋層會每五秒
    被重開一次，最後畫面上疊滿同一個東西。
    """
    state, clock, _ = make_state(idle=10 * 60)
    assert state.poll() is True
    assert state.poll() is None
    assert state.poll() is None


def test_coming_back_stops_it():
    state, clock, _ = make_state(idle=10 * 60)
    assert state.poll() is True

    clock.seconds = 0.0
    assert state.poll() is False
    assert state.active is False
    assert state.poll() is None


def test_switching_it_off_while_it_is_showing_clears_the_screen():
    """
    關掉開關也要收掉。少了這條，使用者關掉功能之後畫面上還留著一層自己不會消失
    的覆蓋層，而且再也不會有事件來收它。
    """
    state, clock, settings = make_state(idle=10 * 60)
    assert state.poll() is True

    settings["enabled"] = False
    assert state.poll() is False
    assert state.active is False


def test_a_disabled_screensaver_never_starts():
    state, clock, _ = make_state(idle=10 * 60, enabled=False)
    assert state.poll() is None
    assert state.active is False


def test_a_platform_with_no_idle_reading_shows_nothing():
    """閒置時間問不到就不要自作主張——寧可不動作，也不要在有人用的時候蓋上去。"""
    settings = {"enabled": True, "idle_minutes": 1, "source": "video"}
    state = ScreensaverState(lambda: settings, lambda: None)
    assert state.poll() is None
    assert state.active is False


def test_losing_the_idle_reading_while_showing_clears_it():
    settings = {"enabled": True, "idle_minutes": 1, "source": "video"}
    readings = [120.0, None]
    state = ScreensaverState(lambda: settings, lambda: readings.pop(0))
    assert state.poll() is True
    assert state.poll() is False


def test_the_threshold_is_the_configured_minutes():
    state, clock, _ = make_state(idle=0.0, idle_minutes=2)
    clock.seconds = 119.0
    assert state.poll() is None
    clock.seconds = 120.0
    assert state.poll() is True


@pytest.mark.parametrize("value,expected", [
    (0, MIN_IDLE_MINUTES),
    (-5, MIN_IDLE_MINUTES),
    (10, 10),
    (99999, MAX_IDLE_MINUTES),
    ("7", 7),
    (None, DEFAULT_IDLE_MINUTES),
    ("nonsense", DEFAULT_IDLE_MINUTES),
])
def test_idle_minutes_are_clamped(value, expected):
    assert clamp_idle_minutes(value) == expected


@pytest.mark.parametrize("value,expected", [
    ("video", "video"),
    ("WEB", "web"),
    ("  gif  ", "gif"),
    ("sound", "video"),
    (None, "video"),
    (17, "video"),
])
def test_unknown_sources_fall_back_to_the_default(value, expected):
    assert normalize_source(value) == expected


def test_every_source_is_something_the_main_window_can_start():
    """
    來源清單和主視窗的對照表必須一致。多一個沒對照的名稱，選了它就什麼都不會發生
    而且不會有任何錯誤——安靜地壞掉。
    """
    from frontengine.ui.main_ui import FrontEngineMainUI

    assert set(SOURCES) == set(FrontEngineMainUI._SCREENSAVER_SOURCES)


def test_the_dialog_offers_a_label_for_every_source():
    from frontengine.ui.dialog.screensaver_dialog import SOURCE_LABEL_KEYS

    assert set(SOURCES) == set(SOURCE_LABEL_KEYS)


class Sentinel:
    """假裝是使用者自己開的覆蓋層，只記得自己有沒有被關掉。"""

    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


def test_it_closes_only_what_it_opened(tmp_path, monkeypatch):
    """
    人回來時只能收掉螢幕保護自己放上去的。使用者在離開前開著的覆蓋層被一起關掉，
    是回到座位才會發現的那種災難，而且沒有任何錯誤訊息。
    Coming back must clear only what the screensaver put there. Taking the user's
    own overlays with it is the kind of loss noticed only on sitting back down,
    and nothing reports it.
    """
    import os

    from frontengine.ui.main_ui import FrontEngineMainUI

    original = os.getcwd()
    os.chdir(tmp_path)
    try:
        window = FrontEngineMainUI(show_system_tray_ray=False, redirect_output=False)
        page = window.video_setting_ui

        mine = Sentinel()
        page.video_widget_list.append(mine)          # 使用者離開前就開著的
        page.ready_to_play = True
        page.video_path = "whatever.mp4"

        theirs = Sentinel()
        monkeypatch.setattr(page, "start_play_video",
                            lambda: page.video_widget_list.append(theirs))

        window._start_screensaver("video")
        assert page.video_widget_list == [mine, theirs]

        window._stop_screensaver()
        assert theirs.closed is True
        assert mine.closed is False
        assert page.video_widget_list == [mine]
        window.close()
    finally:
        os.chdir(original)


def test_a_page_with_nothing_set_up_is_never_started(tmp_path, monkeypatch):
    """
    沒選檔案就不要按開始。每個分頁在那個情況下都會跳 modal 訊息框，而螢幕保護
    正好在沒有人的時候啟動——那個框會擋在畫面上直到有人回來。
    """
    import os

    from frontengine.ui.main_ui import FrontEngineMainUI

    original = os.getcwd()
    os.chdir(tmp_path)
    try:
        window = FrontEngineMainUI(show_system_tray_ray=False, redirect_output=False)
        page = window.video_setting_ui
        page.ready_to_play = False

        started = []
        monkeypatch.setattr(page, "start_play_video", lambda: started.append(True))

        window._start_screensaver("video")
        assert started == []
        window.close()
    finally:
        os.chdir(original)
