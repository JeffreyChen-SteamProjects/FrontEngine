"""
視窗複本：另外開一個小視窗顯示別的視窗的即時畫面。

DWM 那一層是 Win32 邊界，離屏測不到；能測而且值得測的是它周圍的決定——縮放算術、
接不上時不要把空視窗留在畫面上、以及不支援的平台不要假裝成功。

Window replicas. The DWM layer is a Win32 boundary and cannot be exercised
offscreen; what can be tested, and is worth testing, are the decisions around it:
the scaling arithmetic, not leaving an empty window when it cannot attach, and
not pretending to work where it does not.
"""
import pytest

from frontengine.utils.window_replica.dwm_thumbnail import (
    MIN_REPLICA_SIZE, DwmThumbnail, fit_within,
)


@pytest.mark.parametrize("source,bounds,expected", [
    ((1920, 1080), (480, 270), (480, 270)),        # 同比例，剛好貼合
    ((1000, 1000), (480, 270), (270, 270)),        # 正方形受限於高度
    ((400, 300), (480, 270), (360, 270)),          # 放大也保持比例
    ((3840, 1080), (480, 270), (480, 135)),        # 超寬視窗
])
def test_it_keeps_the_aspect_ratio(source, bounds, expected):
    assert fit_within(source, bounds) == expected


def test_a_source_size_of_zero_does_not_divide_by_zero():
    """
    來源尺寸問不到時是 0。這裡如果直接拿來當除數，複本就會在建立的當下炸掉，
    而且是在使用者剛按下按鈕的時候。
    """
    assert fit_within((0, 0), (480, 270)) == (480, 270)
    assert fit_within((1920, 0), (480, 270)) == (480, 270)


def test_it_never_shrinks_below_something_you_can_grab():
    """縮到幾像素寬的複本沒辦法拖也沒辦法關，等於卡在畫面上。"""
    width, height = fit_within((4000, 10), (480, 270))
    assert width >= MIN_REPLICA_SIZE
    assert height >= MIN_REPLICA_SIZE


def test_an_unregistered_thumbnail_answers_without_touching_win32():
    """沒註冊過就呼叫更新或查尺寸不該爆炸，也不該假裝成功。"""
    thumbnail = DwmThumbnail()
    assert thumbnail.registered is False
    assert thumbnail.update(100, 100) is False
    assert thumbnail.source_size() == (0, 0)
    thumbnail.unregister()          # 重複收掉是安全的
    thumbnail.unregister()


def test_registering_where_dwm_does_not_exist_reports_failure(monkeypatch):
    import frontengine.utils.window_replica.dwm_thumbnail as module

    monkeypatch.setattr(module, "available", lambda: False)
    thumbnail = module.DwmThumbnail()
    assert thumbnail.register(1, 2) is False
    assert thumbnail.registered is False


class FakeReplica:
    """假的複本視窗：只記錄自己有沒有被要求開始與關閉。"""

    def __init__(self, handle, title, opacity, parent=None, crop=None):
        self.handle = handle
        self.title = title
        self.opacity = opacity
        self.crop = crop
        self.started = False
        self.closed = False
        self.attach_succeeds = True

    def start(self):
        self.started = True
        return self.attach_succeeds

    def close(self):
        self.closed = True


def test_a_replica_that_cannot_attach_is_not_left_on_screen(tmp_path):
    """
    接不上就要收掉。留一個永遠黑著、又沒有標題列的小視窗在最上層，比什麼都不做
    更糟——使用者不會知道那是什麼，也不容易關掉。
    A replica that cannot attach must be closed. Leaving a permanently black,
    title-bar-less window on top is worse than doing nothing: the user has no
    idea what it is and no obvious way to be rid of it.
    """
    from frontengine.ui.dialog.window_replica_dialog import WindowReplicaDialog

    created = []

    def factory(handle, title, opacity, parent=None, crop=None):
        replica = FakeReplica(handle, title, opacity, parent, crop)
        replica.attach_succeeds = False
        created.append(replica)
        return replica

    dialog = WindowReplicaDialog(lister=lambda: [(1234, "Some window")],
                                 replica_factory=factory)
    dialog.window_list.setCurrentRow(0)

    assert dialog.start_replica() is None
    assert created[0].closed is True
    assert dialog.replica_widget_list == []


def test_a_working_replica_is_remembered_so_it_can_be_closed_later(tmp_path):
    """複本握著 DWM 縮圖這個系統資源，關程式時一定要收，所以必須記著。"""
    from frontengine.ui.dialog.window_replica_dialog import WindowReplicaDialog

    dialog = WindowReplicaDialog(lister=lambda: [(1234, "Some window")],
                                 replica_factory=FakeReplica)
    dialog.window_list.setCurrentRow(0)

    replica = dialog.start_replica()
    assert replica is not None
    assert replica.started is True
    assert dialog.replica_widget_list == [replica]

    dialog.close_all()
    assert replica.closed is True
    assert dialog.replica_widget_list == []


def test_nothing_selected_means_nothing_happens():
    from frontengine.ui.dialog.window_replica_dialog import WindowReplicaDialog

    dialog = WindowReplicaDialog(lister=lambda: [], replica_factory=FakeReplica)
    assert dialog.selected() is None
    assert dialog.start_replica() is None


def test_the_replica_carries_the_chosen_opacity():
    from frontengine.ui.dialog.window_replica_dialog import WindowReplicaDialog

    dialog = WindowReplicaDialog(lister=lambda: [(7, "Window")],
                                 replica_factory=FakeReplica)
    dialog.window_list.setCurrentRow(0)
    dialog.opacity_slider.setValue(45)

    replica = dialog.start_replica()
    assert replica.opacity == 45
    assert replica.handle == 7


# --- 只框一塊 / cropping to part of the source -----------------------------

def test_no_crop_means_the_whole_window():
    from frontengine.utils.window_replica.dwm_thumbnail import crop_rect

    assert crop_rect((1920, 1080), None) is None


def test_a_crop_becomes_pixels_on_the_source():
    from frontengine.utils.window_replica.dwm_thumbnail import crop_rect

    assert crop_rect((1920, 1080), (0.0, 0.0, 1.0, 0.5)) == (0, 0, 1920, 540)
    assert crop_rect((1920, 1080), (0.5, 0.0, 1.0, 1.0)) == (960, 0, 1920, 1080)
    assert crop_rect((800, 600), (0.25, 0.25, 0.75, 0.75)) == (200, 150, 600, 450)


def test_the_crop_follows_the_source_being_resized():
    """
    比例存的意義就在這裡：來源視窗變大之後，框到的還是同一塊，不是原本那些像素。
    Fractions exist for this: after the source is resized the crop still points
    at the same part of it rather than at the old pixels.
    """
    from frontengine.utils.window_replica.dwm_thumbnail import crop_rect

    right_half = (0.5, 0.0, 1.0, 1.0)
    assert crop_rect((1000, 500), right_half) == (500, 0, 1000, 500)
    assert crop_rect((2000, 1000), right_half) == (1000, 0, 2000, 1000)


@pytest.mark.parametrize("crop", [
    (0.5, 0.0, 0.5, 1.0),      # 寬度為零
    (0.0, 0.7, 1.0, 0.7),      # 高度為零
    (0.8, 0.0, 0.2, 1.0),      # 左右顛倒
    (0.0, 0.9, 1.0, 0.1),      # 上下顛倒
])
def test_a_crop_with_no_area_is_refused(crop):
    """
    寬或高為零的來源矩形會讓 DWM 完全不畫，畫面上只剩一塊黑——看起來像壞掉，
    而不是「你框錯了」。寧可整個視窗照舊顯示。
    """
    from frontengine.utils.window_replica.dwm_thumbnail import crop_rect

    assert crop_rect((1920, 1080), crop) is None


def test_a_crop_outside_the_window_is_clamped_not_rejected():
    from frontengine.utils.window_replica.dwm_thumbnail import crop_rect

    assert crop_rect((1000, 1000), (-0.5, -0.5, 2.0, 2.0)) == (0, 0, 1000, 1000)


def test_an_unknown_source_size_cannot_be_cropped():
    from frontengine.utils.window_replica.dwm_thumbnail import crop_rect

    assert crop_rect((0, 0), (0.0, 0.0, 1.0, 0.5)) is None


def test_every_offered_region_produces_a_usable_rectangle():
    """
    對話框上的每個選項都要框得出面積。有一個框不出來的話，選了它就只會得到
    一塊黑，而且沒有任何錯誤訊息。
    """
    from frontengine.ui.dialog.window_replica_dialog import CROP_REGIONS
    from frontengine.utils.window_replica.dwm_thumbnail import crop_rect

    for key, fallback, region in CROP_REGIONS:
        if region is None:
            continue
        rect = crop_rect((1920, 1080), region)
        assert rect is not None, f"{key} selects nothing"
        assert rect[2] > rect[0] and rect[3] > rect[1]


def test_the_chosen_region_reaches_the_replica():
    from frontengine.ui.dialog.window_replica_dialog import CROP_REGIONS, WindowReplicaDialog

    captured = {}

    def factory(handle, title, opacity, parent=None, crop=None):
        captured["crop"] = crop
        return FakeReplica(handle, title, opacity, parent)

    dialog = WindowReplicaDialog(lister=lambda: [(1, "Window")], replica_factory=factory)
    dialog.window_list.setCurrentRow(0)
    index = next(i for i, entry in enumerate(CROP_REGIONS) if entry[2] is not None)
    dialog.crop_combobox.setCurrentIndex(index)

    dialog.start_replica()
    assert captured["crop"] == CROP_REGIONS[index][2]
