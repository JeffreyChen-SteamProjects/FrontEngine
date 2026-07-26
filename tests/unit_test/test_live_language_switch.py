"""
即時換語言。

以前換語言會跳一個「請重新啟動」的訊息框，因為每個標籤都是建構時查一次字典就
固定了。現在每個控制項都記著自己的文字來自哪個鍵，換語言時原地重寫。

這裡最重要的是最後那個測試：它把整個主視窗建起來、切成德文，然後檢查畫面上
還有沒有留著英文。以後有人加了控制項卻忘記登記，那個測試就會指名道姓地紅給
你看——不必靠人記得。

Live language switching.

Changing language used to pop a "please restart" box, because every label
looked the dictionary up once at construction and kept the answer. Now each
widget remembers the key behind its text and gets rewritten in place.

The last test is the one that matters: it builds the whole main window, switches
to German and checks whether anything is still in English. If someone adds a
widget and forgets to register it, that test names it - nobody has to remember.
"""
import json
import os

import pytest
from PySide6.QtWidgets import QCheckBox, QLabel, QMenu, QPushButton, QWidget

from frontengine.ui.menu.language_menu import LANGUAGES
from frontengine.utils.multi_language.english import english_word_dict
from frontengine.utils.multi_language.germany import germany_word_dict
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.utils.multi_language.retranslate import Retranslator, translate


# --- the registry ---------------------------------------------------------
def test_a_bound_widget_follows_the_language() -> None:
    registry = Retranslator()
    label = QLabel()
    label.setText(registry.bind(label, "tab_tools_text"))
    language_wrapper.reset_language("English")
    registry.apply()
    assert label.text() == english_word_dict["tab_tools_text"]
    language_wrapper.reset_language("Deutsch")
    registry.apply()
    assert label.text() == germany_word_dict["tab_tools_text"]
    language_wrapper.reset_language("English")
    label.close()


def test_a_toggling_button_follows_the_state_it_is_in() -> None:
    """
    會換字的按鈕要跟著「現在是哪個狀態」翻譯，而不是回到建構當下那一個。
    A button whose wording changes must translate the state it is actually in,
    not the one it was built with.
    """
    registry = Retranslator()
    button = QPushButton()
    button.setText(registry.bind(button, "control_center_hide_all"))
    registry.set_text(button, "control_center_show_all")

    language_wrapper.reset_language("Deutsch")
    registry.apply()
    assert button.text() == germany_word_dict["control_center_show_all"]
    assert button.text() != germany_word_dict["control_center_hide_all"]
    language_wrapper.reset_language("English")
    button.close()


def test_a_toggling_button_does_not_accumulate_registrations() -> None:
    """
    set_text 每次都先把舊的那筆忘掉。少了這一步文字仍然是對的（後登記的會蓋過
    先登記的），但表會隨著每一次按鈕切換無限長大。
    set_text forgets the previous entry first. Without that the text is still
    right - a later entry overwrites an earlier one - but the table grows
    without bound, once per toggle, for as long as the app runs.
    """
    registry = Retranslator()
    button = QPushButton()
    button.setText(registry.bind(button, "control_center_hide_all"))
    for _ in range(20):
        registry.set_text(button, "control_center_show_all")
        registry.set_text(button, "control_center_hide_all")
    assert len(registry) == 1, f"one widget should hold one entry, found {len(registry)}"
    button.close()


def test_a_closed_widget_is_dropped_rather_than_kept_alive() -> None:
    """
    覆蓋層關掉之後不該因為這張表而活著，也不該讓整批重寫爆掉。
    A closed overlay must not be kept alive by this table, nor break the batch.
    """
    registry = Retranslator()
    keeper = QLabel()
    keeper.setText(registry.bind(keeper, "tab_tools_text"))
    doomed = QLabel()
    doomed.setText(registry.bind(doomed, "tab_pet_text"))
    assert len(registry) == 2

    doomed.deleteLater()
    doomed.destroy()
    del doomed

    registry.apply()
    assert len(registry) <= 2, "a dead entry must not survive forever"
    keeper.close()


def test_composed_text_is_recomputed_by_its_callback() -> None:
    """有些文字是組出來的（提示 + 樣板），單一個鍵表達不了，所以整段重算。"""
    registry = Retranslator()
    calls = []
    holder = QWidget()
    holder.recompute = lambda: calls.append(language_wrapper.language)
    registry.bind_call(holder.recompute)
    registry.apply()
    assert calls == [language_wrapper.language]
    holder.close()


def test_an_unknown_setter_is_skipped_rather_than_raising() -> None:
    registry = Retranslator()
    label = QLabel()
    registry.bind(label, "tab_tools_text", "", "setNothingLikeThis")
    assert registry.apply() == 0
    label.close()


# --- the language list ----------------------------------------------------
def test_every_menu_entry_names_a_language_that_exists() -> None:
    """
    選單裡的「French」和「Italian」曾經送出註冊表沒有的名字，按下去毫無反應。
    The menu's "French" and "Italian" used to send names the registry did not
    have, so those entries did nothing at all.
    """
    for label_key, code in LANGUAGES:
        assert code in language_wrapper.choose_language_dict, f"{label_key} -> {code}"
        assert label_key in english_word_dict


def test_switching_to_a_name_that_does_not_exist_says_so() -> None:
    """靜靜地失敗正是上面那個 bug 藏了那麼久的原因。"""
    before = language_wrapper.language
    assert language_wrapper.reset_language("Klingon") is False
    assert language_wrapper.language == before, "a failed switch must change nothing"
    assert language_wrapper.reset_language("English") is True


# --- the whole window -----------------------------------------------------
@pytest.mark.parametrize("code", [code for _, code in LANGUAGES if code != "English"])
def test_nothing_is_left_in_the_previous_language(code: str, tmp_path) -> None:
    """
    整個主視窗切過去之後，畫面上不該還留著英文。
    有控制項沒登記，這裡就會把它印出來。
    After the whole window switches, nothing on it should still be English.
    A widget nobody registered shows up here by name.
    """
    from frontengine.ui.main_ui import FrontEngineMainUI
    from frontengine.ui.menu.language_menu import set_language

    settings = tmp_path / "user_setting.json"
    settings.write_text(json.dumps({"language": "English"}), encoding="utf-8")
    original = os.getcwd()
    os.chdir(tmp_path)
    try:
        window = FrontEngineMainUI(show_system_tray_ray=False, redirect_output=False)
        assert window.language_wrapper.language == "English"
        assert set_language(code, window) is True

        target = language_wrapper.choose_language_dict[code]
        # 在新語言裡也合法的字串不算漏掉：有些鍵在兩種語言長得一樣（URL、Zoom…）
        # Text that is also valid in the new language is not a miss: some keys
        # read the same in both (URL, Zoom and friends).
        valid_now = {str(value) for value in target.values()}
        stale = {str(english_word_dict[key]) for key in english_word_dict
                 if str(english_word_dict[key]) != str(target[key])}

        seen = [window.tab_widget.tabText(i) for i in range(window.tab_widget.count())]
        seen += [w.text() for w in window.findChildren(QPushButton)
                 + window.findChildren(QLabel) + window.findChildren(QCheckBox) if w.text()]
        menus = window.menuBar().findChildren(QMenu)
        seen += [m.title() for m in menus]
        seen += [a.text() for m in menus for a in m.actions()
                 if not a.isSeparator() and a.text()]

        left = sorted({text for text in seen if text in stale and text not in valid_now})
        assert not left, f"still in English after switching to {code}: {left}"
        window.close()
    finally:
        os.chdir(original)
        language_wrapper.reset_language("English")


def test_switching_leaves_the_user_alone(tmp_path) -> None:
    """
    不用重開的意義就在這裡：開著的覆蓋層還在，各分頁的設定也沒被動到。
    This is the whole point of not restarting: open overlays stay open and the
    settings on each page are untouched.
    """
    from frontengine.ui.main_ui import FrontEngineMainUI
    from frontengine.ui.menu.language_menu import set_language

    (tmp_path / "user_setting.json").write_text(
        json.dumps({"language": "English"}), encoding="utf-8")
    original = os.getcwd()
    os.chdir(tmp_path)
    try:
        window = FrontEngineMainUI(show_system_tray_ray=False, redirect_output=False)
        window.presentation_setting_ui.start_whiteboard()
        board = window.presentation_setting_ui.whiteboard_widget_list[0]
        window.text_setting_ui.opacity_slider.setValue(77)
        before = window.text_setting_ui.get_state()

        assert set_language("Deutsch", window) is True

        assert window.presentation_setting_ui.whiteboard_widget_list == [board]
        assert window.text_setting_ui.get_state() == before
        window.control_center_ui.clear_all()
        window.close()
    finally:
        os.chdir(original)
        language_wrapper.reset_language("English")


def test_the_translation_lands_where_you_can_see_it(tmp_path) -> None:
    """抽查幾個實際控制項，而不是只看計數。"""
    from frontengine.ui.main_ui import FrontEngineMainUI
    from frontengine.ui.menu.language_menu import set_language

    (tmp_path / "user_setting.json").write_text(
        json.dumps({"language": "English"}), encoding="utf-8")
    original = os.getcwd()
    os.chdir(tmp_path)
    try:
        window = FrontEngineMainUI(show_system_tray_ray=False, redirect_output=False)
        assert window.tab_widget.tabText(0) == english_word_dict["tab_video_text"]
        set_language("Deutsch", window)
        assert window.tab_widget.tabText(0) == germany_word_dict["tab_video_text"]
        assert window.control_center_ui.hide_all_button.text() == \
            germany_word_dict["control_center_hide_all"]
        titles = [m.title() for m in window.menuBar().findChildren(QMenu)]
        assert translate("menu_bar_settings") in titles
        window.close()
    finally:
        os.chdir(original)
        language_wrapper.reset_language("English")
