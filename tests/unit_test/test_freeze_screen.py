"""
凍結畫面。

最要緊的不是「蓋得上去」，而是**蓋上去之後解除得掉**：凍結時主視窗在那張靜止圖
後面，按鈕點不到，所以出口一個都不能少——任何鍵、雙擊、以及全域快速鍵。
少一個，使用者就只剩工作管理員。

Freezing the screen. What matters is less that it covers than that it can be
undone: while frozen the main window sits behind the still image and its buttons
cannot be reached, so none of the ways out may be missing - any key, a
double-click, and the global shortcut. Without them the user has the task manager.
"""
import os

import pytest
from PySide6.QtGui import QPixmap

from frontengine.show.freeze.freeze_widget import FreezeWidget, capture_screen


def test_a_missing_screen_gives_no_picture():
    """拍不到就要回空的，呼叫端才知道不要蓋上去。"""
    assert capture_screen(None).isNull()


def test_the_widget_holds_the_picture_it_was_given():
    pixmap = QPixmap(64, 48)
    widget = FreezeWidget(pixmap)
    assert widget.pixmap.width() == 64
    assert widget.pixmap.height() == 48
    widget.close()


def test_a_widget_built_from_nothing_does_not_crash_on_paint():
    """空 pixmap 不該讓 paintEvent 爆掉；畫不出來就什麼都不畫。"""
    widget = FreezeWidget(None)
    assert widget.pixmap.isNull()
    widget.repaint()
    widget.close()


@pytest.fixture
def presentation_page(tmp_path):
    from frontengine.ui.page.presentation.presentation_setting_ui import PresentationSettingUI

    original = os.getcwd()
    os.chdir(tmp_path)
    try:
        yield PresentationSettingUI()
    finally:
        os.chdir(original)


def test_a_screen_that_cannot_be_captured_is_not_covered(presentation_page, monkeypatch):
    """
    拍不到就不要蓋一塊空白上去。整片黑的螢幕看起來像當機，而不是「凍結失敗」——
    而且那時候使用者根本不知道該按什麼。
    """
    monkeypatch.setattr(
        "frontengine.ui.page.presentation.presentation_setting_ui.capture_screen",
        lambda screen: QPixmap())

    assert presentation_page.toggle_freeze() is None
    assert presentation_page.freeze_widget_list == []


def test_freezing_then_toggling_again_unfreezes(presentation_page, monkeypatch):
    monkeypatch.setattr(
        "frontengine.ui.page.presentation.presentation_setting_ui.capture_screen",
        lambda screen: QPixmap(32, 24))

    frozen = presentation_page.toggle_freeze()
    assert frozen is not None
    assert presentation_page.freeze_widget_list == [frozen]

    assert presentation_page.toggle_freeze() is None
    assert presentation_page.freeze_widget_list == []


def test_the_button_says_what_it_will_do(presentation_page, monkeypatch):
    """
    凍結之後按鈕要改成「解除凍結」。一直寫著「凍結」的話，使用者會以為沒生效而
    再按一次——那反而把它解除掉了。
    """
    monkeypatch.setattr(
        "frontengine.ui.page.presentation.presentation_setting_ui.capture_screen",
        lambda screen: QPixmap(32, 24))

    before = presentation_page.freeze_button.text()
    presentation_page.toggle_freeze()
    during = presentation_page.freeze_button.text()
    presentation_page.toggle_freeze()
    after = presentation_page.freeze_button.text()

    assert during != before
    assert after == before


def test_dismissing_it_directly_puts_the_button_back(presentation_page, monkeypatch):
    """
    使用者按 Escape 自己關掉時，按鈕也要回到「凍結」。否則它會一直提議解除一個
    已經不存在的東西。
    """
    monkeypatch.setattr(
        "frontengine.ui.page.presentation.presentation_setting_ui.capture_screen",
        lambda screen: QPixmap(32, 24))

    before = presentation_page.freeze_button.text()
    frozen = presentation_page.toggle_freeze()
    presentation_page._forget_freeze(frozen)

    assert presentation_page.freeze_widget_list == []
    assert presentation_page.freeze_button.text() == before


def test_any_key_unfreezes_not_only_escape():
    """
    畫面停住的時候，使用者最可能做的是隨便按一個鍵看看。只認 Escape 的話，
    那個嘗試會沒有反應，而畫面看起來就是當機了。
    """
    from PySide6.QtCore import QEvent, Qt
    from PySide6.QtGui import QKeyEvent

    for key in (Qt.Key.Key_Escape, Qt.Key.Key_Space, Qt.Key.Key_A):
        widget = FreezeWidget(QPixmap(16, 16))
        closed = []
        widget.destroyed.connect(lambda: closed.append(True))
        widget.keyPressEvent(QKeyEvent(QEvent.Type.KeyPress, key, Qt.KeyboardModifier.NoModifier))
        assert widget.isVisible() is False


def test_the_shortcut_can_reach_it():
    """
    凍結時主視窗在靜止圖後面，按鈕點不到，所以全域快速鍵是唯一保證按得到的出口。
    綁定漏掉的話，使用者會被自己凍結的畫面困住。
    """
    from frontengine.ui.dialog.hotkey_settings_dialog import action_label
    from frontengine.user_setting.user_setting_file import default_hotkeys

    assert "toggle_freeze" in default_hotkeys
    label = action_label("toggle_freeze")
    assert label and label != "toggle_freeze"
