from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtGui import QAction

from frontengine.utils.browser.browser import open_browser
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.multi_language.language_wrapper import language_wrapper

if TYPE_CHECKING:
    from frontengine.ui.main_ui import FrontEngineMainUI


def build_how_to_menu(ui_we_want_to_set: FrontEngineMainUI) -> None:
    """
    建立「文件/教學」選單
    Build the "How To / Documentation" menu
    """
    front_engine_logger.info(f"[HowToMenu] build_how_to_menu | ui={ui_we_want_to_set}")

    # 建立選單 / Create menu
    how_to_menu = ui_we_want_to_set.menu_bar.addMenu(
        language_wrapper.language_word_dict.get("doc_menu_label")
    )
    ui_we_want_to_set.how_to_menu = how_to_menu

    # 建立「開啟文件」動作 / Create "Open Documentation" action
    _add_action(
        how_to_menu,
        language_wrapper.language_word_dict.get("doc_menu_open_doc"),
        lambda: open_browser("https://frontengine.readthedocs.io/en/latest/")
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
