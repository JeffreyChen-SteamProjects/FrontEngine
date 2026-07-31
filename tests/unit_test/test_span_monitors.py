"""
橫跨所有螢幕：一個覆蓋層蓋滿整個桌面，而不是每個螢幕各一個。

離屏只有一個螢幕，所以螢幕清單是注入的。要釘住的是路由決定——橫跨時**只能**建
一個覆蓋層，而且尺寸是所有螢幕的聯集，不是把寬度加起來。

Spanning: one overlay over the whole desktop instead of one per screen.

Offscreen has a single screen, so the screen list is injected. What is pinned
down is the routing: spanning must build exactly one overlay, sized to the union
of the screens rather than the sum of their widths.
"""
from PySide6.QtCore import QRect

from frontengine.ui.page.utils import (
    SPAN_ALL_DATA, build_target_monitor_combobox, dispatch_to_monitors, resolve_preferred_monitor,
    resolve_span, virtual_desktop_geometry,
)


class FakeScreen:
    def __init__(self, rect):
        self._rect = rect

    def geometry(self):
        return self._rect

    def availableGeometry(self):
        return self._rect


class FakeWidget:
    def __init__(self):
        self.geometry = None
        self.shown = False
        self.raised = False

    def setGeometry(self, rect):
        self.geometry = rect

    def show(self):
        self.shown = True

    def raise_(self):
        self.raised = True


SIDE_BY_SIDE = [FakeScreen(QRect(0, 0, 1920, 1080)), FakeScreen(QRect(1920, 0, 1920, 1080))]
STACKED = [FakeScreen(QRect(0, 0, 1920, 1080)), FakeScreen(QRect(0, 1080, 1920, 1080))]
MIXED = [FakeScreen(QRect(0, 0, 2560, 1440)), FakeScreen(QRect(2560, 300, 1920, 1080))]


def test_the_union_covers_screens_in_a_row():
    assert virtual_desktop_geometry(SIDE_BY_SIDE) == QRect(0, 0, 3840, 1080)


def test_the_union_covers_screens_stacked_vertically():
    """
    螢幕不一定排成一直線。把寬度加起來的做法在上下排列時會算出一條又寬又扁的
    區域，覆蓋層就只蓋到上面那半。
    """
    assert virtual_desktop_geometry(STACKED) == QRect(0, 0, 1920, 2160)


def test_the_union_covers_screens_of_different_sizes_and_offsets():
    """
    兩個不同尺寸、垂直位置也錯開的螢幕：聯集要把兩個都包進去。

    高度是 1440 而不是第二個螢幕的底部 1380——聯集要取兩者的最大範圍，
    第一個螢幕比較高，不能被第二個的位置蓋過去。
    """
    assert virtual_desktop_geometry(MIXED) == QRect(0, 0, 4480, 1440)


def test_spanning_builds_exactly_one_overlay_covering_everything():
    built = []

    def factory(monitor):
        built.append(monitor)
        return FakeWidget()

    dispatch_to_monitors(
        parent=None, show_all_screen=False, factory=factory,
        present_primary=lambda widget: pytest_fail("primary path used"),
        present_on_monitor=lambda *args: pytest_fail("per-monitor path used"),
        span_all_screens=True, screens=SIDE_BY_SIDE,
    )
    assert len(built) == 1


def test_the_spanned_overlay_is_sized_to_the_whole_desktop():
    created = []

    def factory(monitor):
        widget = FakeWidget()
        created.append(widget)
        return widget

    dispatch_to_monitors(
        parent=None, show_all_screen=False, factory=factory,
        present_primary=lambda widget: None, present_on_monitor=lambda *args: None,
        span_all_screens=True, screens=SIDE_BY_SIDE,
    )
    widget = created[0]
    assert widget.geometry == QRect(0, 0, 3840, 1080)
    assert widget.shown is True


def test_spanning_on_a_single_screen_falls_back_to_the_normal_path():
    """
    只有一個螢幕時，橫跨和一般顯示是同一件事。這裡不能走橫跨那條路，因為它用的是
    setGeometry 而不是全螢幕，會少掉單螢幕本來的行為。
    """
    primary = []
    dispatch_to_monitors(
        parent=None, show_all_screen=False, factory=lambda monitor: FakeWidget(),
        present_primary=lambda widget: primary.append(widget),
        present_on_monitor=lambda *args: None,
        span_all_screens=True, screens=[FakeScreen(QRect(0, 0, 1920, 1080))],
    )
    assert len(primary) == 1


def test_not_spanning_still_goes_per_monitor():
    presented = []
    dispatch_to_monitors(
        parent=None, show_all_screen=True, factory=lambda monitor: FakeWidget(),
        present_primary=lambda widget: None,
        present_on_monitor=lambda widget, monitor, index: presented.append(index),
        span_all_screens=False, screens=SIDE_BY_SIDE,
    )
    assert presented == [0, 1]


def test_the_span_entry_only_appears_when_there_is_more_than_one_screen():
    """
    單螢幕時列出「橫跨所有螢幕」，選了會和平常一模一樣，使用者只會懷疑自己漏掉
    了什麼設定。
    """
    single = build_target_monitor_combobox(screens=[FakeScreen(QRect(0, 0, 1920, 1080))])
    assert single.findData(SPAN_ALL_DATA) == -1

    dual = build_target_monitor_combobox(screens=SIDE_BY_SIDE)
    assert dual.findData(SPAN_ALL_DATA) >= 0


def test_the_span_entry_is_not_mistaken_for_a_monitor_index():
    """
    選了橫跨時，「要哪一個螢幕」必須回答 None。回答成某個索引的話，覆蓋層會被送去
    那一個螢幕，橫跨就完全沒有發生。
    """
    combobox = build_target_monitor_combobox(screens=SIDE_BY_SIDE)
    combobox.setCurrentIndex(combobox.findData(SPAN_ALL_DATA))

    assert resolve_span(combobox) is True
    assert resolve_preferred_monitor(combobox) is None


def test_a_monitor_choice_is_not_mistaken_for_spanning():
    combobox = build_target_monitor_combobox(screens=SIDE_BY_SIDE)
    combobox.setCurrentIndex(combobox.findData(1))

    assert resolve_span(combobox) is False
    assert resolve_preferred_monitor(combobox) == 1


def test_no_combobox_means_no_spanning():
    assert resolve_span(None) is False


def pytest_fail(message):
    raise AssertionError(message)
