"""
把視窗搬到下一個螢幕的測試。

幾何全部是純函式，螢幕清單直接以 (x, y, w, h) 餵進去，所以「兩台不同解析度的
螢幕」這種情境不必真的接兩台螢幕。Win32 那一段（前景視窗、實際搬移）以注入
取代。

Tests for moving a window to the next monitor.

The geometry is pure and screens come in as (x, y, w, h), so "two screens at
different resolutions" needs no second monitor. The Win32 half - foreground
window, the actual move - is injected.
"""
from frontengine.utils.window_pin.monitor_move import (
    clamp_into, mapped_rect, move_to_next_monitor, next_index, overlap_area, plan_move,
    qt_screen_rects, screen_index_for, screen_rects,
)
from frontengine.utils.window_pin.window_layout import MIN_SIZE

LEFT = (0, 0, 1920, 1080)
RIGHT = (1920, 0, 2560, 1440)
SMALL = (1920, 0, 1280, 720)


def test_overlap_area_is_zero_when_apart() -> None:
    assert overlap_area((0, 0, 10, 10), (20, 20, 10, 10)) == 0
    assert overlap_area((0, 0, 10, 10), (5, 5, 10, 10)) == 25


def test_the_screen_is_chosen_by_area_not_by_corner() -> None:
    """
    跨螢幕擺放的視窗，左上角可能還在上一台，但人看到的主體在另一台。
    A straddling window can have its corner on one screen while what the user
    sees is on the other.
    """
    straddling = (1820, 100, 800, 600)  # 100px on the left screen, 700 on the right
    assert screen_index_for(straddling, [LEFT, RIGHT]) == 1


def test_a_window_off_every_screen_has_no_index() -> None:
    assert screen_index_for((-4000, -4000, 100, 100), [LEFT, RIGHT]) is None


def test_the_next_index_wraps() -> None:
    assert next_index(0, 2) == 1
    assert next_index(1, 2) == 0
    assert next_index(0, 3, step=2) == 2


def test_a_single_screen_has_nowhere_to_go() -> None:
    assert next_index(0, 1) is None
    assert next_index(None, 2) is None
    assert plan_move((10, 10, 400, 300), [LEFT]) is None


def test_proportions_survive_a_different_resolution() -> None:
    """
    右半邊佔三分之一的視窗，搬到解析度不同的螢幕之後還是右半邊的三分之一。
    這正是 Windows 內建的貼齊做不到的事。
    A window filling a third of the right half stays that on a screen of a
    different resolution - which is what the built-in snap does not do.
    """
    window = (960, 0, 640, 540)  # half across, a third wide, half tall on LEFT
    x, y, width, height = mapped_rect(window, LEFT, RIGHT)
    assert x == RIGHT[0] + RIGHT[2] // 2
    assert width == round(640 / 1920 * RIGHT[2])
    assert height == round(540 / 1080 * RIGHT[3])
    assert y == RIGHT[1]


def test_a_window_moved_to_a_smaller_screen_stays_on_it() -> None:
    """從大螢幕搬到小螢幕時，不能有一半掉在畫面外。"""
    window = (1500, 800, 400, 280)
    x, y, width, height = mapped_rect(window, LEFT, SMALL)
    assert x >= SMALL[0] and y >= SMALL[1]
    assert x + width <= SMALL[0] + SMALL[2]
    assert y + height <= SMALL[1] + SMALL[3]


def test_a_window_is_never_shrunk_to_nothing() -> None:
    tiny = mapped_rect((0, 0, 1, 1), LEFT, SMALL)
    assert tiny[2] >= MIN_SIZE and tiny[3] >= MIN_SIZE


def test_planning_moves_to_the_other_screen() -> None:
    plan = plan_move((10, 10, 400, 300), [LEFT, RIGHT])
    assert plan is not None
    assert plan[0] >= RIGHT[0], "it landed on the right-hand screen"


def test_a_rectangle_is_nudged_back_inside_its_screen() -> None:
    assert clamp_into((1900, 100, 400, 300), LEFT) == (1520, 100, 400, 300)
    assert clamp_into((-50, -50, 400, 300), LEFT) == (0, 0, 400, 300)
    assert clamp_into((100, 100, 400, 300), LEFT) == (100, 100, 400, 300), "already inside"


def test_a_window_bigger_than_the_screen_goes_to_the_corner() -> None:
    """比螢幕還大的視窗貼左上角：至少標題列和關閉鈕點得到。"""
    assert clamp_into((500, 500, 4000, 3000), LEFT) == (0, 0, 4000, 3000)


def test_the_window_is_settled_after_the_os_rescales_it() -> None:
    """
    真機發現：跨到 DPI 不同的螢幕時，Windows 會在我們的 SetWindowPos 之後自己
    把視窗放大（實測 100% -> 125% 是 x1.25）。原本剛好貼齊右緣的視窗會被推出
    畫面，所以落地後要再夾一次。
    Found on real hardware: crossing a DPI boundary, Windows scales the window
    up after our SetWindowPos (measured x1.25 from a 100% to a 125% screen). A
    window flush against the right edge gets pushed off, so it is clamped again
    after landing.
    """
    moves = []
    landed = {}

    def mover(handle, x, y, width, height):
        moves.append((x, y, width, height))
        # 模擬 OS 的 DPI 放大：只在第一次搬移之後發生
        # Simulate the OS scaling, which only follows the first move.
        landed["rect"] = (x, y, int(width * 1.25), int(height * 1.25)) if len(moves) == 1 \
            else (x, y, width, height)
        return True

    def reader(handle):
        return landed.get("rect", (1500, 800, 400, 280))

    assert move_to_next_monitor(
        screens=_fake_screens([LEFT, SMALL]), handle=42,
        geometry_reader=reader, mover=mover) is True
    assert len(moves) == 2, "it moved, saw the overflow, and settled it"
    x, y, width, height = moves[-1]
    assert x + width <= SMALL[0] + SMALL[2], "back inside the target screen"
    assert y + height <= SMALL[1] + SMALL[3]


def test_a_window_that_lands_cleanly_is_not_moved_twice() -> None:
    """沒有凸出去就不要多送一次 SetWindowPos——那會讓視窗閃一下。"""
    moves = []

    def mover(handle, x, y, width, height):
        moves.append((x, y, width, height))
        return True

    move_to_next_monitor(
        screens=_fake_screens([LEFT, RIGHT]), handle=42,
        geometry_reader=lambda handle: moves[-1] if moves else (10, 10, 400, 300),
        mover=mover)
    assert len(moves) == 1


def test_the_move_uses_the_injected_pieces() -> None:
    moved = []

    def mover(handle, x, y, width, height):
        moved.append((handle, x, y, width, height))
        return True

    result = move_to_next_monitor(
        screens=[], handle=42,
        geometry_reader=lambda handle: (10, 10, 400, 300),
        mover=mover)
    assert result is False, "no screens were supplied, so there is nowhere to go"

    result = move_to_next_monitor(
        screens=_fake_screens([LEFT, RIGHT]), handle=42,
        geometry_reader=lambda handle: (10, 10, 400, 300),
        mover=mover)
    assert result is True
    assert moved and moved[0][0] == 42


def test_explicit_screens_are_read_through_qt() -> None:
    """
    傳進來的 screens 一律走 Qt 那條路。正式執行時不傳，才會去問 Win32——
    因為 Qt 給的是邏輯像素，而 SetWindowPos 用實體像素，混合 DPI 下差 25%。
    Screens passed in always go through Qt. Live runs pass none and ask Win32
    instead: Qt reports logical pixels while SetWindowPos speaks physical ones,
    and on mixed DPI they differ by 25%.
    """
    fakes = _fake_screens([LEFT, RIGHT])
    assert screen_rects(fakes) == [LEFT, RIGHT]
    assert qt_screen_rects(fakes) == [LEFT, RIGHT]


def test_nothing_happens_without_a_window() -> None:
    assert move_to_next_monitor(screens=_fake_screens([LEFT, RIGHT]), handle=0) is False
    assert move_to_next_monitor(
        screens=_fake_screens([LEFT, RIGHT]), handle=42,
        geometry_reader=lambda handle: None) is False


class _FakeScreen:
    """只需要 availableGeometry() 的假 QScreen。"""

    def __init__(self, rect) -> None:
        self._rect = rect

    def availableGeometry(self):  # noqa: N802 - Qt's own spelling
        class _Rect:
            def __init__(self, values):
                self._values = values

            def x(self):
                return self._values[0]

            def y(self):
                return self._values[1]

            def width(self):
                return self._values[2]

            def height(self):
                return self._values[3]

        return _Rect(self._rect)


def _fake_screens(rects):
    return [_FakeScreen(rect) for rect in rects]
