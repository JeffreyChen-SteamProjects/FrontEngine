"""
虛擬桌面綁定的測試。

**測不到的部分先講清楚**：CI 上沒有第二個虛擬桌面，也沒有辦法切過去，所以真正
的 `IVirtualDesktopManager` 呼叫在這裡不會被執行。探測函式是注入的，驗的是
「誰該被藏、誰該被放回來」這一段邏輯——那也正是會出錯的地方。

Tests for the virtual desktop pin.

**What is not covered, stated up front**: CI has no second virtual desktop and
no way to switch to one, so the real `IVirtualDesktopManager` call is never
exercised here. The probe is injected and what is asserted is the decision -
who gets hidden, who comes back - which is where the mistakes live anyway.
"""
import sys

from PySide6.QtWidgets import QWidget

from frontengine.utils.virtual_desktop.virtual_desktop import (
    DesktopVisibility, VirtualDesktopService, available, is_window_on_current_desktop,
    widget_handle,
)


class FakeOverlay(QWidget):
    """有 handle、記得自己被 hide/show 過幾次的假覆蓋層。"""

    def __init__(self, handle: int) -> None:
        super().__init__()
        self._handle = handle
        self.hidden_times = 0
        self.shown_times = 0

    def winId(self):  # noqa: N802 - Qt's own spelling
        return self._handle

    def hide(self) -> None:
        self.hidden_times += 1

    def show(self) -> None:
        self.shown_times += 1


def on_desktops(*present):
    """回傳一個探測函式：handle 在 present 裡就算「在目前的桌面上」。"""
    allowed = set(present)
    return lambda handle: handle in allowed


def test_availability_follows_the_platform() -> None:
    assert available() is (sys.platform == "win32")


def test_an_unknown_answer_is_not_a_no() -> None:
    """
    「不知道」和「不在這個桌面」必須分開。混為一談的話，沒有這個 API 的機器上
    每一個覆蓋層都會被判成不在，然後全部被藏起來。
    "Unknown" and "not here" have to stay apart: conflated, every overlay on a
    machine without the API reads as absent and all of them get hidden.
    """
    assert is_window_on_current_desktop(123, probe=lambda handle: None) is None
    assert is_window_on_current_desktop(0, probe=lambda handle: True) is None, "no handle, no answer"


def test_a_raising_probe_is_treated_as_unknown() -> None:
    def broken(handle):
        raise OSError("COM went away")

    assert is_window_on_current_desktop(123, probe=broken) is None


def test_widgets_off_the_current_desktop_are_hidden() -> None:
    here, there = FakeOverlay(1), FakeOverlay(2)
    visibility = DesktopVisibility()
    decision = visibility.decide([here, there], probe=on_desktops(1))
    assert decision["hide"] == [there]
    assert decision["show"] == []
    assert visibility.hidden_count() == 1


def test_a_widget_is_only_hidden_once() -> None:
    """每秒輪詢一次，重複下 hide 只是白做工，也會蓋掉使用者自己的操作。"""
    there = FakeOverlay(2)
    visibility = DesktopVisibility()
    probe = on_desktops()
    assert visibility.decide([there], probe=probe)["hide"] == [there]
    assert visibility.decide([there], probe=probe)["hide"] == [], "already hidden"


def test_coming_back_restores_only_what_was_hidden_here() -> None:
    """
    使用者自己按了「全部隱藏」的覆蓋層，不該因為切了一次桌面就被放回來。
    An overlay the user hid with "hide all" must not reappear just because a
    desktop was switched.
    """
    ours, theirs = FakeOverlay(1), FakeOverlay(2)
    visibility = DesktopVisibility()
    visibility.decide([ours, theirs], probe=on_desktops())      # both away
    decision = visibility.decide([ours, theirs], probe=on_desktops(1, 2))
    assert decision["show"] == [ours, theirs]
    # theirs 從來沒被這個服務藏過的情境
    fresh = DesktopVisibility()
    assert fresh.decide([theirs], probe=on_desktops(2))["show"] == []


def test_a_closed_overlay_is_forgotten() -> None:
    """
    handle 會被作業系統回收再配給別的視窗。留著舊紀錄的話，某個不相干的
    視窗會被當成「我藏的」而放回來。
    Handles get recycled. A stale record would let this service "restore" a
    window it never hid.
    """
    gone = FakeOverlay(2)
    visibility = DesktopVisibility()
    visibility.decide([gone], probe=on_desktops())
    assert visibility.hidden_count() == 1
    visibility.decide([], probe=on_desktops())
    assert visibility.hidden_count() == 0, "the overlay is gone, so is the record"


def test_the_service_hides_and_restores_through_the_widgets() -> None:
    here, there = FakeOverlay(1), FakeOverlay(2)
    service = VirtualDesktopService(widgets_provider=lambda: [here, there],
                                    probe=on_desktops(1))
    service.poll_once()
    assert there.hidden_times == 1, "the one on the other desktop was hidden"
    assert here.hidden_times == 0, "the one on this desktop was left alone"
    service.set_probe(on_desktops(1, 2))
    service.poll_once()
    assert there.shown_times == 1


def test_stopping_brings_back_what_it_hid() -> None:
    """
    少了這一步，關掉功能之後那些覆蓋層就永遠不見，畫面上也沒有線索。
    Without this, switching the feature off leaves them hidden for good with
    nothing on screen to explain it.
    """
    there = FakeOverlay(2)
    service = VirtualDesktopService(widgets_provider=lambda: [there], probe=on_desktops())
    service.start()
    service.poll_once()
    assert there.hidden_times == 1
    service.stop()
    assert there.shown_times == 1
    assert service.running() is False


def test_a_failing_widget_source_does_not_break_the_poll() -> None:
    def broken():
        raise RuntimeError("page torn down")

    service = VirtualDesktopService(widgets_provider=broken, probe=on_desktops())
    assert service.poll_once() == {"hide": [], "show": []}


def test_a_widget_without_a_handle_is_skipped() -> None:
    class NoHandle(QWidget):
        def winId(self):  # noqa: N802
            raise RuntimeError("not realised")

    widget = NoHandle()
    try:
        assert widget_handle(widget) is None
        assert DesktopVisibility().decide([widget], probe=on_desktops())["hide"] == []
    finally:
        widget.close()
