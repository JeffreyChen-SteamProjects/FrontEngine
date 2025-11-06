from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from frontengine.utils.logging.loggin_instance import front_engine_logger

if TYPE_CHECKING:
    from frontengine.ui.main_ui import FrontEngineMainUI

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QSystemTrayIcon, QMenu


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

    def _create_actions(self) -> None:
        """建立系統匣選單動作 / Create system tray menu actions"""
        self.hide_main_window_action = QAction("Hide", self)
        self.hide_main_window_action.triggered.connect(self.main_window.hide)
        self.menu.addAction(self.hide_main_window_action)

        self.maximized_main_window_action = QAction("Maximized", self)
        self.maximized_main_window_action.triggered.connect(self.main_window.showMaximized)
        self.menu.addAction(self.maximized_main_window_action)

        self.normal_main_window_action = QAction("Normal", self)
        self.normal_main_window_action.triggered.connect(self.main_window.showNormal)
        self.menu.addAction(self.normal_main_window_action)

        self.close_main_window_action = QAction("Close", self)
        self.close_main_window_action.triggered.connect(self.close_all)
        self.menu.addAction(self.close_main_window_action)

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