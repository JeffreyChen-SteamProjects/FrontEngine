from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMessageBox

from frontengine.utils.browser.browser import open_browser
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper

if TYPE_CHECKING:
    from frontengine.ui.main_ui import FrontEngineMainUI


def build_help_menu(ui_we_want_to_set: FrontEngineMainUI) -> None:
    """
    建立「說明」選單
    Build the Help menu for the main UI
    """
    front_engine_logger.info(f"[HelpMenu] build_help_menu | ui={ui_we_want_to_set}")

    help_menu = ui_we_want_to_set.menu_bar.addMenu(
        language_wrapper.language_word_dict.get("help_menu_label")
    )
    ui_we_want_to_set.help_menu = help_menu

    # --- 建立動作 / Create actions ---
    _add_action(
        help_menu,
        language_wrapper.language_word_dict.get("help_menu_open_issue"),
        lambda: open_browser("https://github.com/Integration-Automation/FrontEngine/issues")
    )

    _add_action(
        help_menu,
        language_wrapper.language_word_dict.get("how_to_critical_exit_action"),
        lambda: how_to_critical_exit(ui_we_want_to_set)
    )


def _add_action(menu, label: str, callback) -> QAction:
    """
    建立 QAction 並加入選單
    Create a QAction and add it to the menu
    """
    action = QAction(label, menu)
    action.triggered.connect(callback)
    menu.addAction(action)
    return action


def how_to_critical_exit(ui_we_want_to_set: FrontEngineMainUI) -> None:
    """
    顯示「如何強制退出」訊息
    Show a message box explaining how to critical exit
    """
    front_engine_logger.info(f"[HelpMenu] how_to_critical_exit | ui={ui_we_want_to_set}")
    message_box = QMessageBox(ui_we_want_to_set)
    message_box.setText(language_wrapper.language_word_dict.get("how_to_critical_exit"))
    message_box.exec()  # 使用 exec() 讓使用者必須確認
