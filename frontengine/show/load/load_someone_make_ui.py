from PySide6.QtGui import QScreen
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QWidget

from frontengine.utils.exception.exceptions import FrontEngineLoadUIException


def load_someone_make_ui(ui_path: str, show_all_screen: bool = False):
    ui = load_ui(ui_path)
    if show_all_screen:
        ui.showFullScreen()
    else:
        monitors = QScreen.virtualSiblings(ui.screen())
        for screen in monitors:
            monitor = screen.availableGeometry()
            new_ui = ui
            new_ui.move(monitor.left(), monitor.top())
            new_ui.showFullScreen()


def load_ui(ui_path: str) -> QWidget:
    ui = QUiLoader().load(ui_path)
    if not ui:
        raise FrontEngineLoadUIException
    return ui
