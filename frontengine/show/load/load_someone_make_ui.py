from typing import Optional, List

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QWidget

from frontengine.utils.exception.exceptions import FrontEngineLoadUIException
from frontengine.utils.logging.loggin_instance import front_engine_logger

# 載入的視窗沒有 parent，Python 這邊不留參考就會立刻被回收，視窗根本不會出現。
# A loaded window has no parent, so without a reference on the Python side it is
# collected the moment this function returns and never appears at all.
_loaded_ui_widgets: List[QWidget] = []


def _forget_closed_ui() -> None:
    """把已被 Qt 銷毀的視窗從清單剔除，免得一直累積。"""
    alive: List[QWidget] = []
    for widget in _loaded_ui_widgets:
        try:
            widget.isVisible()
        except RuntimeError:  # 底層 C++ 物件已消滅 / underlying C++ object is gone
            continue
        alive.append(widget)
    _loaded_ui_widgets[:] = alive


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
    _forget_closed_ui()

    if show_all_screen:
        # 一個 widget 不可能同時待在多台螢幕上，每台各載入一份
        # One widget cannot sit on several screens at once, so load one per screen.
        for screen in QGuiApplication.screens():
            _present_ui(load_ui_file(ui_path), screen.availableGeometry().topLeft())
    else:
        _present_ui(load_ui_file(ui_path), None)


def _present_ui(ui: QWidget, top_left) -> None:
    """全螢幕顯示一個載入好的視窗，並保留參考直到它被關閉。"""
    ui.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
    if top_left is not None:
        ui.move(top_left)
    ui.showFullScreen()
    _loaded_ui_widgets.append(ui)


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
