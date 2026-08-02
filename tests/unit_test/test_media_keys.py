"""
媒體控制的測試。真的送出媒體鍵需要 Windows，也需要一個認得媒體鍵的播放器，
兩者在 CI 上都沒有——所以這裡注入一個假的 sender，驗證「送了什麼」，
而不是「播放器有沒有動」。後者不是這個模組能回答的事。

Tests for media transport. Actually sending a media key needs Windows and a
media-key aware player, neither of which exists on CI, so a fake sender is
injected and what gets *sent* is asserted - not whether a player reacted, which
this module cannot answer anyway.
"""
import sys

from frontengine.utils.media_keys.media_keys import (
    ACTION_NEXT, ACTION_PLAY_PAUSE, ACTION_PREVIOUS, ACTION_STOP, ACTIONS,
    KEYEVENTF_EXTENDEDKEY, KEYEVENTF_KEYUP, VK_MEDIA_NEXT_TRACK, VK_MEDIA_PLAY_PAUSE,
    VK_MEDIA_PREV_TRACK, VK_MEDIA_STOP, available, is_media_action, key_code, send_media_key,
)
from frontengine.utils.remote.remote_server import ALLOWED_ACTIONS
from frontengine.user_setting.user_setting_file import default_hotkeys


class RecordingSender:
    """記下每一次 keybd_event 呼叫。"""

    def __init__(self) -> None:
        self.calls = []

    def __call__(self, code, scan, flags, extra) -> None:
        self.calls.append((code, scan, flags, extra))


def test_each_action_maps_to_its_virtual_key() -> None:
    assert key_code(ACTION_PLAY_PAUSE) == VK_MEDIA_PLAY_PAUSE
    assert key_code(ACTION_NEXT) == VK_MEDIA_NEXT_TRACK
    assert key_code(ACTION_PREVIOUS) == VK_MEDIA_PREV_TRACK
    assert key_code(ACTION_STOP) == VK_MEDIA_STOP


def test_a_non_media_action_is_not_claimed() -> None:
    """
    主視窗是先比對既有動作、再落到媒體控制的。這裡認錯一個名字，
    「全部隱藏」就會變成按下播放鍵。
    The main window checks its own actions first and falls through to media.
    Claiming a name that is not ours would turn "hide all" into a play press.
    """
    for action in ("hide_all", "show_all", "mute_all", "toggle_lock", "", None):
        assert not is_media_action(action), action
        assert key_code(action) is None


def test_sending_presses_and_releases_the_key() -> None:
    """只送按下不送放開，某些播放器會當成鍵一直被按著。"""
    sender = RecordingSender()
    assert send_media_key(ACTION_NEXT, sender=sender) is True
    assert len(sender.calls) == 2, "one press and one release"
    press, release = sender.calls
    assert press[0] == release[0] == VK_MEDIA_NEXT_TRACK
    assert press[2] == KEYEVENTF_EXTENDEDKEY
    assert release[2] == KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP


def test_an_unknown_action_sends_nothing() -> None:
    sender = RecordingSender()
    assert send_media_key("not_a_media_action", sender=sender) is False
    assert sender.calls == []


def test_a_failing_sender_is_reported_not_raised() -> None:
    """快速鍵是在 UI 執行緒上分派的，這裡讓例外逃出去就是整個程式掛掉。"""
    def broken(code, scan, flags, extra):
        raise OSError("no user32 here")

    assert send_media_key(ACTION_PLAY_PAUSE, sender=broken) is False


def test_it_degrades_quietly_when_the_platform_cannot_send() -> None:
    """
    非 Windows 上不該丟例外，只是什麼都不做——和其他平台限定功能一致。

    這裡**刻意不真的呼叫沒有 sender 的版本**：在 Windows 上那會真的按下
    播放鍵，跑一次測試就把開發者正在聽的音樂暫停掉。改成讓取得 sender 的那一步
    失敗，走的是同一條降級路徑。
    Off Windows it degrades quietly rather than raising, like every other
    platform-specific feature here.

    This deliberately does **not** call the senderless form: on Windows that
    would really press play/pause and pause whatever the developer is listening
    to, once per test run. Failing the sender lookup exercises the same path.
    """
    def unavailable(code, scan, flags, extra):
        raise OSError("media keys are Windows only")

    assert send_media_key(ACTION_PLAY_PAUSE, sender=unavailable) is False
    assert available() is (sys.platform == "win32")


def test_every_action_is_reachable_from_a_hotkey() -> None:
    """
    綁定不存在的話，這些動作只有程式內部叫得到，使用者按不到。
    Without a binding these actions exist only for internal callers and no user
    can reach them.
    """
    for action in (ACTION_PLAY_PAUSE, ACTION_NEXT, ACTION_PREVIOUS):
        assert action in default_hotkeys, action


def test_the_transport_actions_are_reachable_from_the_phone() -> None:
    for action in (ACTION_PLAY_PAUSE, ACTION_NEXT, ACTION_PREVIOUS):
        assert action in ALLOWED_ACTIONS, action


def test_the_remote_cannot_ask_for_anything_outside_the_list() -> None:
    """遙控的允許清單是白名單，媒體控制加進去之後也還是白名單。"""
    assert ACTION_STOP not in ALLOWED_ACTIONS, "only what the UI actually offers"
    assert set(ACTIONS) - set(ALLOWED_ACTIONS) == {ACTION_STOP}


def test_no_media_hotkey_collides_with_another_action() -> None:
    combos = list(default_hotkeys.values())
    assert len(combos) == len(set(combos)), "two actions on one combo means one is unreachable"
