from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from frontengine.ui.main_ui import FrontEngineMainUI

from frontengine.utils.browser.browser import open_browser
from PySide6.QtGui import QAction
from frontengine.utils.multi_language.language_wrapper import language_wrapper


def build_help_menu(ui_we_want_to_set: FrontEngineMainUI) -> None:
    ui_we_want_to_set.help_menu = ui_we_want_to_set.menu_bar.addMenu(
        language_wrapper.language_word_dict.get("help_menu_label")
    )
    ui_we_want_to_set.help_menu.open_issue_action = QAction(
        language_wrapper.language_word_dict.get("help_menu_open_issue")
    )
    ui_we_want_to_set.help_menu.open_issue_action.triggered.connect(
        lambda: open_browser("https://github.com/Integration-Automation/FrontEngine/issues")
    )
    ui_we_want_to_set.help_menu.addAction(
        ui_we_want_to_set.help_menu.open_issue_action
    )

