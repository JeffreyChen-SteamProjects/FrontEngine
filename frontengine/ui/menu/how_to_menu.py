from __future__ import annotations
from typing import TYPE_CHECKING

from frontengine.utils.browser.browser import open_browser

if TYPE_CHECKING:
    from frontengine.ui.main_ui import FrontEngineMainUI
from PySide6.QtGui import QAction

from frontengine.utils.multi_language.language_wrapper import language_wrapper


def build_how_to_menu(ui_we_want_to_set: FrontEngineMainUI) -> None:
    ui_we_want_to_set.how_to_menu = ui_we_want_to_set.menu_bar.addMenu(
        language_wrapper.language_word_dict.get("doc_menu_label")
    )
    ui_we_want_to_set.how_to_menu.open_doc_action = QAction(
        language_wrapper.language_word_dict.get("doc_menu_open_doc")
    )
    ui_we_want_to_set.how_to_menu.open_doc_action.triggered.connect(
        lambda: open_browser("https://frontengine.readthedocs.io/en/latest/")
    )
    ui_we_want_to_set.how_to_menu.addAction(
        ui_we_want_to_set.how_to_menu.open_doc_action
    )
