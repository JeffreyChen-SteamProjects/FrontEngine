from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMessageBox

from frontengine.ui.dialog.how_to_use_dialog import HowToUseDialog
from frontengine.utils.browser.browser import open_browser
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper
from frontengine.utils.multi_language.retranslate import retranslator, translate

if TYPE_CHECKING:
    from frontengine.ui.main_ui import FrontEngineMainUI


def build_help_menu(ui_we_want_to_set: FrontEngineMainUI) -> None:
    """
    建立「說明」選單
    Build the Help menu for the main UI
    """
    front_engine_logger.info(f"[HelpMenu] build_help_menu | ui={ui_we_want_to_set}")

    help_menu = ui_we_want_to_set.menu_bar.addMenu(translate("help_menu_label", "Help menu"))
    retranslator.bind(help_menu, "help_menu_label", "Help menu", "setTitle")
    ui_we_want_to_set.help_menu = help_menu

    # --- 建立動作 / Create actions ---
    # 使用說明放第一個：第一次打開程式的人最先需要的就是它
    # Usage first: it is what someone opening this for the first time needs.
    _add_action(
        help_menu,
        "how_to_use_action",
        lambda: show_how_to_use(ui_we_want_to_set),
        "How to use..."
    )

    # 也要能從選單開。只能用快速鍵叫出來的「快速鍵速查表」是個笑話：不知道快速鍵
    # 的人正是最需要它的人。
    # It has to be reachable from the menu too. A shortcut sheet you can only open
    # with a shortcut is a joke: the person who does not know the shortcuts is
    # exactly who needs it.
    _add_action(
        help_menu,
        "shortcut_sheet_action",
        lambda: ui_we_want_to_set.toggle_shortcut_sheet(),
        "Shortcut list..."
    )

    _add_action(
        help_menu,
        "help_menu_open_issue",
        lambda: open_browser("https://github.com/Integration-Automation/FrontEngine/issues")
    )

    _add_action(
        help_menu,
        "how_to_critical_exit_action",
        lambda: how_to_critical_exit(ui_we_want_to_set)
    )


def _add_action(menu, key: str, callback, fallback: str = "") -> QAction:
    """
    建立 QAction 並加入選單，同時記住它的文字來自哪個鍵，換語言時才跟得上。
    Create a QAction, add it to the menu, and remember which key its text came
    from so a language change reaches it.
    """
    action = QAction(translate(key, fallback), menu)
    retranslator.bind(action, key, fallback)
    action.triggered.connect(callback)
    menu.addAction(action)
    return action


def show_how_to_use(ui_we_want_to_set: FrontEngineMainUI) -> None:
    """開啟使用說明對話框。"""
    front_engine_logger.info("[HelpMenu] show_how_to_use")
    dialog = HowToUseDialog(ui_we_want_to_set)
    ui_we_want_to_set.how_to_use_dialog = dialog
    dialog.show()


def how_to_critical_exit(ui_we_want_to_set: FrontEngineMainUI) -> None:
    """
    顯示「如何強制退出」訊息
    Show a message box explaining how to critical exit
    """
    front_engine_logger.info(f"[HelpMenu] how_to_critical_exit | ui={ui_we_want_to_set}")
    message_box = QMessageBox(ui_we_want_to_set)
    message_box.setText(language_wrapper.language_word_dict.get("how_to_critical_exit"))
    message_box.exec()  # 使用 exec() 讓使用者必須確認
