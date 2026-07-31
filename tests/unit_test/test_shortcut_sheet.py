"""
快速鍵速查表：把目前實際生效的綁定列出來。

排版是純函式，所以「顯示的內容對不對」不必開視窗就能驗。要釘住的是它讀的是
**實際綁定**而不是另一份手抄的清單——手抄的那份改了快速鍵之後就會開始騙人。

The shortcut cheat sheet lists the bindings actually in force. The rows come from
a pure function, so what it says can be checked without opening a window. What is
pinned down is that it reads the *real* bindings rather than a hand-kept copy,
because a hand-kept copy starts lying the moment a shortcut is rebound.
"""
import pytest

from frontengine.show.shortcuts.shortcut_sheet import build_sheet, pretty_combo, sheet_rows


@pytest.mark.parametrize("combo,expected", [
    ("<ctrl>+<shift>+<f12>", "Ctrl + Shift + F12"),
    ("<ctrl>+<shift>+l", "Ctrl + Shift + L"),
    ("<ctrl>+<shift>+<up>", "Ctrl + Shift + Up"),
    ("<alt>+<space>", "Alt + Space"),
    ("<cmd>+<esc>", "Cmd + Esc"),
])
def test_combos_are_written_the_way_fingers_read_them(combo, expected):
    """
    使用者是拿這個對照自己的手指，不是在讀設定檔，所以尖括號和小寫都要去掉。
    """
    assert pretty_combo(combo) == expected


@pytest.mark.parametrize("combo", ["", None, "+", "<>"])
def test_a_broken_combo_does_not_produce_junk(combo):
    assert pretty_combo(combo) == ""


def test_rows_come_from_the_bindings_in_force():
    bindings = {"<ctrl>+<shift>+<f12>": "close_all", "<ctrl>+<shift>+l": "toggle_lock"}
    rows = sheet_rows(bindings, lambda action: {"close_all": "Close all",
                                                "toggle_lock": "Lock"}[action])
    assert ("Ctrl + Shift + F12", "Close all") in rows
    assert ("Ctrl + Shift + L", "Lock") in rows


def test_rows_are_sorted_by_what_they_do():
    """
    依動作排序而不是依按鍵：使用者是先想到「我要關掉全部」才去找按鍵，不是反過來。
    """
    bindings = {"<ctrl>+1": "zebra", "<ctrl>+2": "apple", "<ctrl>+3": "mango"}
    rows = sheet_rows(bindings, lambda action: action)
    assert [description for _, description in rows] == ["apple", "mango", "zebra"]


def test_empty_or_broken_entries_are_skipped():
    bindings = {"": "close_all", "<ctrl>+a": "", "<ctrl>+b": "real"}
    rows = sheet_rows(bindings, lambda action: action)
    assert rows == [("Ctrl + B", "real")]


def test_nothing_bound_means_no_window():
    """
    一個空白的黑色矩形什麼也沒說明。沒有綁定就不要開，讓呼叫端自己決定要不要
    講一句話。
    """
    assert build_sheet({}, lambda action: action) is None


def test_every_default_shortcut_has_a_description():
    """
    每個預設快速鍵都要有看得懂的說明。少一個的話，速查表上會出現一行內部代號，
    而使用者完全不知道那是什麼。
    """
    from frontengine.ui.dialog.hotkey_settings_dialog import action_label
    from frontengine.user_setting.user_setting_file import default_hotkeys

    for action in default_hotkeys:
        label = action_label(action)
        assert label and label != action, f"{action} shows its internal name"


def test_the_sheet_and_the_hotkey_dialog_agree():
    """
    兩邊共用同一張對照表。各記一份的話，改了說明只會改到其中一邊，使用者會在
    兩個地方看到同一個功能的兩個名字。
    """
    from frontengine.ui.dialog.hotkey_settings_dialog import _ACTION_LABELS, action_label

    for action in _ACTION_LABELS:
        assert action_label(action)


def test_an_unknown_action_still_shows_something():
    """手動編過設定檔而多出來的動作不該讓速查表整個爆掉。"""
    from frontengine.ui.dialog.hotkey_settings_dialog import action_label

    assert action_label("something_invented") == "something_invented"
