from typing import Optional, List

from PySide6.QtGui import QScreen
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QWidget

from frontengine.utils.exception.exceptions import FrontEngineLoadUIException
from frontengine.utils.logging.loggin_instance import front_engine_logger


def load_extend_ui_file(ui_path: str, show_all_screen: bool = False) -> None:
    """
    載入並顯示 UI 檔案
    Load and display a UI file

    :param ui_path: UI 檔案路徑 / Path to the UI file
    :param show_all_screen: 是否顯示在所有螢幕上 / Show on all screens
    """
    front_engine_logger.info(
        f"[load_extend_ui_file] ui_path={ui_path}, show_all_screen={show_all_screen}"
    )

    ui: QWidget = load_ui_file(ui_path)

    if show_all_screen:
        ui.showFullScreen()
    else:
        # 取得所有螢幕並在每個螢幕上顯示 UI
        # Get all monitors and display UI on each
        monitors: List[QScreen] = QScreen.virtualSiblings(ui.screen())
        for screen in monitors:
            monitor_geometry = screen.availableGeometry()
            ui.move(monitor_geometry.left(), monitor_geometry.top())
            ui.showFullScreen()


def load_ui_file(ui_path: str) -> QWidget:
    """
    載入 UI 檔案
    Load a UI file

    :param ui_path: UI 檔案路徑 / Path to the UI file
    :return: QWidget 物件 / QWidget object
    :raises FrontEngineLoadUIException: 若載入失敗 / If loading fails
    """
    front_engine_logger.info(f"[load_ui_file] ui_path={ui_path}")
    ui: QWidget = QUiLoader().load(ui_path)

    if not ui:
        front_engine_logger.error(f"[load_ui_file] Failed to load UI: {ui_path}")
        raise FrontEngineLoadUIException(f"Failed to load UI file: {ui_path}")

    return ui


def read_extend_ui(ui: QWidget) -> Optional[QWidget]:
    """
    驗證並回傳 UI 物件
    Validate and return UI object

    :param ui: QWidget 物件 / QWidget object
    :return: QWidget 或 None / QWidget or None
    """
    front_engine_logger.info(f"[read_extend_ui] ui={ui}")

    if not isinstance(ui, QWidget):
        return None
    return ui
