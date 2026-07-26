"""
控制中心的整批操作測試：重點在「其他分頁註冊進來的覆蓋層」也要真的關得掉。

在這之前，「全部關閉」只清掉最早那幾個分頁自己的清單，後來加的覆蓋層
（塗鴉、放大鏡、白板、準心、色盲濾鏡、儀表板…）它一個都碰不到，會留在
螢幕上。同一顆按鈕的隱藏／顯示卻是好的，所以只看畫面很難發現。

The control center's batch actions, with the emphasis on overlays other pages
registered: those have to close too.

Before this, "close all" only emptied the original pages' own lists and never
touched anything registered later - annotation, magnifier, whiteboard,
crosshair, colour-vision filter, dashboards - so they stayed on screen. Hide
and show from the same panel worked, which is what made it easy to miss.
"""
from typing import List

import pytest
from PySide6.QtWidgets import QWidget

from frontengine.ui.page.control_center.control_center_ui import ControlCenterUI


class _StubPage:
    """只提供整批操作會用到的清單 / Just the lists the batch actions look at."""

    def __init__(self, attribute: str) -> None:
        setattr(self, attribute, [])

    def close_scene(self) -> None:
        """場景頁的介面 / The scene page's interface."""


def _control_center() -> ControlCenterUI:
    return ControlCenterUI(
        video_setting_ui=_StubPage("video_widget_list"),
        image_setting_ui=_StubPage("image_widget_list"),
        web_setting_ui=_StubPage("web_widget_list"),
        gif_setting_ui=_StubPage("gif_widget_list"),
        sound_player_setting_ui=_StubPage("sound_widget_list"),
        text_setting_ui=_StubPage("text_widget_list"),
        scene_setting_ui=_StubPage("scene_widget_list"),
        particle_setting_ui=_StubPage("particle_list"),
        redirect_output=False,
    )


@pytest.fixture(name="centre")
def _centre() -> ControlCenterUI:
    centre = _control_center()
    yield centre
    centre.close()


def _overlay() -> QWidget:
    widget = QWidget()
    widget.show()
    return widget


def test_closing_everything_reaches_an_overlay_another_page_registered(centre) -> None:
    registered: List[QWidget] = [_overlay(), _overlay()]
    centre.register_overlay_source(lambda: registered)

    centre.clear_all()

    assert registered == [], "the page's own list must end up empty"


def test_the_original_pages_still_end_up_empty(centre) -> None:
    centre.video_setting_ui.video_widget_list.append(_overlay())
    centre.image_setting_ui.image_widget_list.append(_overlay())

    centre.clear_all()

    assert centre.video_setting_ui.video_widget_list == []
    assert centre.image_setting_ui.image_widget_list == []


def test_hiding_and_showing_reach_a_registered_overlay(centre) -> None:
    registered = [_overlay()]
    centre.register_overlay_source(lambda: registered)

    centre.hide_all()
    assert registered[0].isVisible() is False
    centre.show_all()
    assert registered[0].isVisible() is True


def test_a_source_that_hands_back_a_copy_still_gets_its_widgets_closed(centre) -> None:
    """
    桌布頁是以螢幕編號為鍵的 dict，交回來的是新的 list——清空那份複本沒有
    意義，但裡面的 widget 還是得關掉。
    The wallpaper page keys its overlays by monitor and hands back a fresh list.
    Emptying that copy means nothing, but the widgets in it must still close.
    """
    kept = {1: _overlay()}
    centre.register_overlay_source(lambda: list(kept.values()))

    centre.clear_all()

    assert kept[1].isVisible() is False


def test_a_registered_cleanup_runs_after_a_batch_close(centre) -> None:
    """覆蓋層都關光了，全域輸入監聽那類東西也該跟著收掉。"""
    calls = []
    centre.register_cleanup(lambda: calls.append("released"))

    centre.clear_all()

    assert calls == ["released"]


def test_one_failing_cleanup_does_not_stop_the_others(centre) -> None:
    calls = []

    def explode() -> None:
        raise RuntimeError("no listener")

    centre.register_cleanup(explode)
    centre.register_cleanup(lambda: calls.append("still ran"))

    centre.clear_all()

    assert calls == ["still ran"]


def test_a_dead_overlay_does_not_stop_the_batch(centre) -> None:
    """
    使用者自己關掉的覆蓋層底層物件已經沒了，清單裡卻還留著參考；
    碰到它會丟 RuntimeError，不能因此讓整批操作停在半路。
    A widget the user already closed is gone underneath while its reference
    lingers; touching it raises RuntimeError, which must not halt the batch.
    """
    dead, alive = _overlay(), _overlay()
    registered = [dead, alive]
    centre.register_overlay_source(lambda: registered)
    dead.close()
    dead.deleteLater()
    dead.destroy()

    centre.clear_all()

    assert registered == []
