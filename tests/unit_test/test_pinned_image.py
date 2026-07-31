"""
把截下來的一塊畫面釘在螢幕上。

縮放是純算術，所以不必開視窗就能驗。要釘住的是兩個會讓使用者卡住的邊界：縮到
太小的圖既拖不動也關不掉，以及沒有截過任何東西時不要開一個空白視窗——那看起來
會像截圖失敗。

Pinning a captured piece of screen. The zooming is pure arithmetic, so it needs no
window. Two boundaries that would strand the user are pinned down: an image zoomed
too small can be neither dragged nor closed, and pinning with nothing captured
must not open an empty window, which would read as the capture having failed.
"""
import pytest
from PySide6.QtGui import QPixmap

from frontengine.show.pinned.pinned_image import (
    MAX_ZOOM, MIN_PINNED_SIZE, MIN_ZOOM, clamp_zoom, zoom_size,
)


def test_zooming_keeps_the_aspect_ratio():
    assert zoom_size((400, 200), 1.0) == (400, 200)
    assert zoom_size((400, 200), 2.0) == (800, 400)
    assert zoom_size((400, 200), 0.5) == (200, 100)


def test_it_never_shrinks_below_something_you_can_grab():
    """
    縮到剩幾像素的圖既拖不動也雙擊不到，就這樣卡在畫面最上層——比不能縮小更糟。
    """
    width, height = zoom_size((400, 200), 0.001)
    assert width >= MIN_PINNED_SIZE
    assert height >= MIN_PINNED_SIZE


@pytest.mark.parametrize("zoom,expected", [
    (0.0, MIN_ZOOM),
    (-3.0, MIN_ZOOM),
    (1.0, 1.0),
    (99.0, MAX_ZOOM),
    ("2", 2.0),
    (None, 1.0),
    ("nonsense", 1.0),
])
def test_the_zoom_factor_is_clamped(zoom, expected):
    assert clamp_zoom(zoom) == expected


def test_an_empty_pixmap_does_not_divide_by_zero():
    """空的 pixmap 尺寸是 0；直接拿來乘除會在建立視窗的當下就炸掉。"""
    assert zoom_size((0, 0), 2.0) == (MIN_PINNED_SIZE, MIN_PINNED_SIZE)


def test_a_pinned_widget_starts_at_the_captured_size():
    from frontengine.show.pinned.pinned_image import PinnedImageWidget

    pixmap = QPixmap(320, 180)
    widget = PinnedImageWidget(pixmap)
    assert widget.base_size() == (320, 180)
    assert widget.zoom == 1.0
    widget.close()


def test_applying_zoom_resizes_the_widget():
    from frontengine.show.pinned.pinned_image import PinnedImageWidget

    widget = PinnedImageWidget(QPixmap(320, 180))
    widget.apply_zoom(2.0)
    assert widget.zoom == 2.0
    expected_width, expected_height = zoom_size((320, 180), 2.0)
    assert widget.width() == expected_width
    assert widget.height() == expected_height
    widget.close()


def test_pinning_with_nothing_captured_opens_nothing(tmp_path):
    """
    沒截過東西就按「釘選上一張」，開一個空白視窗會讓人以為截圖壞了。什麼都不做
    比較誠實。
    """
    import os

    from frontengine.ui.page.tools.tools_setting_ui import ToolsSettingUI

    original = os.getcwd()
    os.chdir(tmp_path)
    try:
        page = ToolsSettingUI()
        assert page.last_capture is None
        assert page.pin_last_capture() is None
        assert page.pinned_widget_list == []
    finally:
        os.chdir(original)


def test_a_pinned_capture_is_remembered_and_can_be_closed(tmp_path):
    """
    釘住的圖是最上層視窗，關程式時一定要收——不然會留在畫面上，而且來源程式
    已經不在了，使用者只能自己去工作管理員。
    """
    import os

    from frontengine.ui.page.tools.tools_setting_ui import ToolsSettingUI

    original = os.getcwd()
    os.chdir(tmp_path)
    try:
        page = ToolsSettingUI()
        page.last_capture = QPixmap(120, 90)

        pinned = page.pin_last_capture()
        assert pinned is not None
        assert page.pinned_widget_list == [pinned]

        page.close_pinned()
        assert page.pinned_widget_list == []
    finally:
        os.chdir(original)


def test_several_captures_can_be_pinned_at_once(tmp_path):
    """釘兩張參考圖是常見用法，不能後一張把前一張踢掉。"""
    import os

    from frontengine.ui.page.tools.tools_setting_ui import ToolsSettingUI

    original = os.getcwd()
    os.chdir(tmp_path)
    try:
        page = ToolsSettingUI()
        page.last_capture = QPixmap(100, 100)
        first = page.pin_last_capture()
        second = page.pin_last_capture()

        assert first is not second
        assert page.pinned_widget_list == [first, second]
        page.close_pinned()
    finally:
        os.chdir(original)
