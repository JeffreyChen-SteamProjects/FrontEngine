from typing import Union, List

from PySide6.QtGui import QScreen
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QWidget

from frontengine.utils.exception.exceptions import FrontEngineLoadUIException
from frontengine.utils.logging.loggin_instance import front_engine_logger


def load_extend_ui_file(ui_path: str, show_all_screen: bool = False) -> None:
    front_engine_logger.info("load_someone_make_ui.py load_extend_ui_file "
                             f"ui_path: {ui_path} "
                             f"show_all_screen: {show_all_screen}")
    ui: QWidget = load_ui_file(ui_path)
    if show_all_screen:
        ui.showFullScreen()
    else:
        monitors: List[QScreen] = QScreen.virtualSiblings(ui.screen())
        for screen in monitors:
            monitor = screen.availableGeometry()
            new_ui = ui
            new_ui.move(monitor.left(), monitor.top())
            new_ui.showFullScreen()


def load_ui_file(ui_path: str) -> QWidget:
    front_engine_logger.info("load_someone_make_ui.py load_extend_ui_file "
                             f"ui_path: {ui_path}")
    ui: QWidget = QUiLoader().load(ui_path)
    if not ui:
        raise FrontEngineLoadUIException
    return ui


def read_extend_ui(ui: QWidget) -> Union[QWidget, None]:
    front_engine_logger.info("load_someone_make_ui.py load_extend_ui_file "
                             f"ui: {ui}")
    if isinstance(ui, QWidget) is False:
        return
    else:
        return ui

