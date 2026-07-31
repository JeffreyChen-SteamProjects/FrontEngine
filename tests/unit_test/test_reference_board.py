"""
參考圖板：一塊畫布上放好幾張圖。

排版是純算術、篩選檔案也不需要視窗，所以這裡驗的是兩件會安靜出錯的事：全部疊在
原點的話開起來只看得到一張（使用者以為只載入了一張），以及讀不進來的檔案如果放行，
圖板上會出現看不見的空白，看起來就是「有一張圖不見了」。

A reference board. The layout is arithmetic and the filtering needs no window, so
what is checked here are two things that fail quietly: stacked at the origin the
board shows one picture with the rest underneath - it looks as though only one
loaded - and an unreadable file let through becomes an invisible blank, which
looks like a picture went missing.
"""
import pytest
from PySide6.QtGui import QPixmap

from frontengine.show.reference.reference_board import (
    ITEM_GAP, columns_for, grid_positions, readable_images,
)


def test_pictures_are_spread_out_not_stacked():
    """
    全部放在 (0, 0) 的話，開起來看到的是一張圖、其他都壓在下面，使用者會以為
    只載入成功一張。
    """
    positions = grid_positions(4, item_size=100, columns=2, gap=10)
    assert len(set(positions)) == 4


def test_the_grid_wraps_at_the_column_count():
    positions = grid_positions(5, item_size=100, columns=2, gap=10)
    assert positions == [(0, 0), (110, 0), (0, 110), (110, 110), (0, 220)]


def test_no_pictures_means_no_positions():
    assert grid_positions(0) == []
    assert grid_positions(-3) == []


@pytest.mark.parametrize("count,preferred,expected", [
    (1, 3, 1),
    (2, 3, 2),
    (3, 3, 3),
    (7, 3, 3),
    (5, 1, 1),
    (0, 3, 0),
])
def test_fewer_pictures_than_columns_use_their_own_number(count, preferred, expected):
    """
    三張圖用三欄，不要排成兩欄然後右邊空一大塊。
    """
    assert columns_for(count, preferred) == expected


def test_the_default_layout_has_a_gap_between_pictures():
    """沒有間隔的話幾張圖會邊貼邊，看起來像一張拼接圖而不是幾張參考。"""
    positions = grid_positions(2, item_size=200, columns=2)
    assert positions[1][0] == 200 + ITEM_GAP


def test_only_real_images_are_kept(tmp_path):
    good = tmp_path / "good.png"
    QPixmap(20, 20).save(str(good))

    broken = tmp_path / "broken.png"
    broken.write_bytes(b"this is not a picture")

    wrong_kind = tmp_path / "notes.txt"
    wrong_kind.write_text("hello", encoding="utf-8")

    missing = tmp_path / "gone.png"

    kept = readable_images([str(good), str(broken), str(wrong_kind), str(missing)])
    assert kept == [str(good)]


def test_nothing_in_means_nothing_out():
    assert readable_images([]) == []
    assert readable_images(None) == []


def test_a_board_lays_out_what_it_accepted(tmp_path):
    from frontengine.show.reference.reference_board import ReferenceBoardWidget

    paths = []
    for index in range(3):
        path = tmp_path / f"pic{index}.png"
        QPixmap(40, 30).save(str(path))
        paths.append(str(path))

    board = ReferenceBoardWidget(item_size=100, columns=2)
    assert board.add_images(paths) == 3
    assert len(board.items) == 3
    assert len({(item.pos().x(), item.pos().y()) for item in board.items}) == 3
    board.close()


def test_unreadable_files_do_not_become_invisible_blanks(tmp_path):
    """
    讀不進來的檔案要在加進圖板之前就擋掉。放行的話畫布上會多一塊看不見的空白，
    使用者只會覺得有一張圖不見了。
    """
    from frontengine.show.reference.reference_board import ReferenceBoardWidget

    good = tmp_path / "good.png"
    QPixmap(20, 20).save(str(good))
    broken = tmp_path / "broken.png"
    broken.write_bytes(b"nope")

    board = ReferenceBoardWidget()
    assert board.add_images([str(good), str(broken)]) == 1
    assert len(board.items) == 1
    board.close()


def test_pictures_can_be_taken_off_the_board(tmp_path):
    from frontengine.show.reference.reference_board import ReferenceBoardWidget

    paths = []
    for index in range(2):
        path = tmp_path / f"pic{index}.png"
        QPixmap(20, 20).save(str(path))
        paths.append(str(path))

    board = ReferenceBoardWidget()
    board.add_images(paths)
    board.items[0].setSelected(True)

    assert board.remove_selected() == 1
    assert len(board.items) == 1
    board.close()


def test_removing_with_nothing_selected_removes_nothing(tmp_path):
    from frontengine.show.reference.reference_board import ReferenceBoardWidget

    path = tmp_path / "pic.png"
    QPixmap(20, 20).save(str(path))

    board = ReferenceBoardWidget()
    board.add_images([str(path)])
    assert board.remove_selected() == 0
    assert len(board.items) == 1
    board.close()


def test_the_board_is_reachable_from_the_control_center(tmp_path):
    """
    圖板是置頂視窗。控制中心的「全部關閉」看不到它的話，使用者就只能一塊一塊
    自己找出來關。
    """
    import os

    from frontengine.ui.page.image.image_setting_ui import ImageSettingUI

    original = os.getcwd()
    os.chdir(tmp_path)
    try:
        page = ImageSettingUI()
        assert hasattr(page, "board_widget_list")
        assert page.board_widget_list == []
    finally:
        os.chdir(original)
