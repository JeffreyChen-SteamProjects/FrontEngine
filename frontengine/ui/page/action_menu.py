"""Compact menus that retain the existing button callbacks and live state."""
from __future__ import annotations

from PySide6.QtCore import QEvent, QObject
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QPushButton, QToolButton, QWidget

from frontengine.utils.multi_language.retranslate import retranslator


class ActionMenu(QToolButton):
    """Expose secondary commands without duplicating their behavior or state."""

    def __init__(self, buttons: tuple[QPushButton, ...], title_key: str = "ui_more_actions",
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("actionMenu")
        self.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        retranslator.bind(self, title_key)
        retranslator.bind(self, title_key, setter="setAccessibleName")
        self.setMenu(QMenu(self))
        self._commands: list[tuple[QPushButton, QAction]] = []
        for button in buttons:
            button.setParent(self)
            button.hide()
            action = QAction(self)
            action.triggered.connect(lambda _checked=False, target=button: target.click())
            self.menu().addAction(action)
            self._commands.append((button, action))
            button.installEventFilter(self)
        self.menu().aboutToShow.connect(self.refresh)
        retranslator.bind_call(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        """Reflect translated labels, toggles and availability before opening."""
        for button, action in self._commands:
            action.setText(button.text())
            action.setEnabled(button.isEnabled())
            action.setCheckable(button.isCheckable())
            action.setChecked(button.isChecked())
            action.setToolTip(button.toolTip())
            action.setIcon(button.icon())

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        """Reflect availability changes made by the command's owning page."""
        if event.type() in (QEvent.Type.EnabledChange, QEvent.Type.ToolTipChange):
            self.refresh()
        return super().eventFilter(watched, event)
