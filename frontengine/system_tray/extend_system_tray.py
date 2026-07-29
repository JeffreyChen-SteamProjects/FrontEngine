from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from frontengine.utils.logging.loggin_instance import front_engine_logger

if TYPE_CHECKING:
    from frontengine.ui.main_ui import FrontEngineMainUI

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QSystemTrayIcon, QMenu

from frontengine.utils.multi_language.retranslate import retranslator, translate


class ExtendSystemTray(QSystemTrayIcon):
    """
    ExtendSystemTray: 系統匣圖示控制器
    ExtendSystemTray: A system tray icon controller with menu actions
    """

    def __init__(self, main_window: FrontEngineMainUI, menu: Optional[QMenu] = None):
        """
        初始化 ExtendSystemTray
        Initialize ExtendSystemTray

        :param main_window: 主視窗 / Main application window
        :param menu: 可選的自訂選單 / Optional custom menu
        """
        front_engine_logger.info(f"[ExtendSystemTray] Init | main_window={main_window}")
        super().__init__(parent=main_window)

        self.main_window = main_window
        self.menu: QMenu = menu if menu else QMenu()

        # 建立選單動作 / Create menu actions
        self._create_actions()

        # 設定選單 / Set context menu
        self.setContextMenu(self.menu)

        # 綁定點擊事件 / Connect activation event
        self.activated.connect(self.clicked)

    def _add_action(self, key: str, fallback: str, callback) -> QAction:
        """
        建立一個選單項目，並登記它的文字來自哪個鍵。沒登記的話換語言不會傳到
        系統匣：主視窗都翻好了，右下角的選單還停在上一個語言。
        Create a menu item and register which key its text comes from. Without
        that registration a language change never reaches the tray: the main
        window is retranslated while the corner menu stays in the old language.
        """
        action = QAction(translate(key, fallback), self)
        retranslator.bind(action, key, fallback)
        action.triggered.connect(callback)
        self.menu.addAction(action)
        return action

    def _create_actions(self) -> None:
        """建立系統匣選單動作 / Create system tray menu actions"""
        self.hide_main_window_action = self._add_action(
            "tray_hide_window", "Hide window", self.main_window.hide)
        self.maximized_main_window_action = self._add_action(
            "tray_maximize_window", "Maximize window", self.main_window.showMaximized)
        self.normal_main_window_action = self._add_action(
            "tray_normal_window", "Restore window", self.main_window.showNormal)

        # 覆蓋層快捷控制 / Overlay quick controls
        self.menu.addSeparator()
        self.hide_all_overlays_action = self._add_action(
            "control_center_hide_all", "Hide all", lambda: self._overlay_call("hide_all"))
        self.show_all_overlays_action = self._add_action(
            "control_center_show_all", "Show all", lambda: self._overlay_call("show_all"))
        self.mute_all_overlays_action = self._add_action(
            "control_center_mute_all", "Mute all", lambda: self._overlay_call("toggle_mute_all"))
        self.close_all_overlays_action = self._add_action(
            "control_center_close_all", "Close all", lambda: self._overlay_call("clear_all"))

        self.menu.addSeparator()
        self.close_main_window_action = self._add_action(
            "tray_close_app", "Quit FrontEngine", self.close_all)

    def _overlay_call(self, method_name: str) -> None:
        """
        呼叫控制中心的覆蓋層操作，並防護控制中心尚未建立的情況。
        Invoke a control-center overlay action, guarding against the control
        center not being ready.
        """
        front_engine_logger.info(f"[ExtendSystemTray] _overlay_call | {method_name}")
        control_center = getattr(self.main_window, "control_center_ui", None)
        method = getattr(control_center, method_name, None)
        if callable(method):
            method()

    def close_all(self) -> None:
        """
        關閉應用程式
        Close the application
        """
        front_engine_logger.info("[ExtendSystemTray] close_all")
        self.setVisible(False)
        self.main_window.close()

    def clicked(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """
        系統匣點擊事件
        System tray click event
        """
        front_engine_logger.info(f"[ExtendSystemTray] clicked | reason={reason}")
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.main_window.showMaximized()