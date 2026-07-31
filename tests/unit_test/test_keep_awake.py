"""
保持喚醒：覆蓋層放著的時候別讓螢幕睡著。

平台呼叫是邊界，離屏測不到；能測而且非測不可的是**放開**這件事。執行緒執行狀態
跟著行程活著，忘了還原的話，使用者關掉選項、甚至關掉整個程式之後螢幕還是不會睡，
而且畫面上沒有任何線索說明是誰造成的。

Keep awake. The platform call is a boundary; what can and must be tested is the
*releasing*. The execution state lives as long as the process, so forgetting to
restore it leaves the display refusing to sleep after the user switched the
option off - or closed the application - with nothing on screen to say why.
"""
import sys

import pytest

from frontengine.utils.keep_awake.keep_awake import KeepAwake, available, helper_command


@pytest.fixture
def fake_platform(monkeypatch):
    """把平台呼叫換成可觀察的假物件。"""
    calls = []

    def fake_state(keep_display_on, release=False):
        calls.append(("release" if release else "hold", keep_display_on))
        return True

    monkeypatch.setattr(KeepAwake, "_windows_state", staticmethod(fake_state))
    monkeypatch.setattr(KeepAwake, "_start_helper", lambda self: calls.append(("hold", True)) or True)
    monkeypatch.setattr(KeepAwake, "_stop_helper", lambda self: calls.append(("release", True)))
    monkeypatch.setattr("frontengine.utils.keep_awake.keep_awake.available", lambda: True)
    return calls


def test_it_starts_inactive():
    assert KeepAwake().active is False


def test_enabling_holds_it(fake_platform):
    service = KeepAwake()
    assert service.enable() is True
    assert service.active is True
    assert ("hold", True) in fake_platform


def test_enabling_twice_does_not_hold_it_twice(fake_platform):
    """
    重複按下不能疊加。在 macOS 與 Linux 上那會多開一個常駐行程，而只有最後一個
    handle 會被記住——先前那個就永遠留著，螢幕再也不會睡。
    """
    service = KeepAwake()
    service.enable()
    holds = [call for call in fake_platform if call[0] == "hold"]
    service.enable()
    assert [call for call in fake_platform if call[0] == "hold"] == holds


def test_disabling_releases_it(fake_platform):
    service = KeepAwake()
    service.enable()
    service.disable()
    assert service.active is False
    assert ("release", True) in fake_platform


def test_disabling_when_it_was_never_on_does_nothing(fake_platform):
    """沒開過就關，不該去動系統狀態——那會把別的程式的設定一起還原掉。"""
    service = KeepAwake()
    service.disable()
    assert fake_platform == []


def test_disabling_twice_is_safe(fake_platform):
    service = KeepAwake()
    service.enable()
    service.disable()
    releases = len([call for call in fake_platform if call[0] == "release"])
    service.disable()
    assert len([call for call in fake_platform if call[0] == "release"]) == releases


def test_it_can_be_turned_on_again_after_being_released(fake_platform):
    service = KeepAwake()
    service.enable()
    service.disable()
    assert service.enable() is True
    assert service.active is True


def test_a_platform_that_cannot_do_it_reports_failure(monkeypatch):
    """
    做不到就要回報失敗，呼叫端才能把選單的勾勾收回去。回報成功的話使用者會看到
    一個勾著卻毫無作用的選項。
    """
    monkeypatch.setattr("frontengine.utils.keep_awake.keep_awake.available", lambda: False)
    service = KeepAwake()
    assert service.enable() is False
    assert service.active is False


def test_a_failed_hold_leaves_it_inactive(monkeypatch):
    monkeypatch.setattr("frontengine.utils.keep_awake.keep_awake.available", lambda: True)
    monkeypatch.setattr(KeepAwake, "_windows_state", staticmethod(lambda *args, **kwargs: False))
    monkeypatch.setattr(KeepAwake, "_start_helper", lambda self: False)
    service = KeepAwake()
    assert service.enable() is False
    assert service.active is False


def test_the_helper_argv_is_literal():
    """
    非 Windows 平台是靠一個常駐小程式。argv 必須全部寫死，沒有任何外部輸入——
    這條測試也是那個 nosec 註解的依據。
    """
    for platform in ("darwin", "linux"):
        from frontengine.utils.keep_awake.keep_awake import _HELPERS

        command = _HELPERS[platform]
        assert all(isinstance(part, str) for part in command)
        assert all("{" not in part and "%" not in part for part in command)


@pytest.mark.skipif(sys.platform != "win32", reason="Windows reports availability without a helper")
def test_windows_is_always_available():
    assert available() is True
    assert helper_command() is None
