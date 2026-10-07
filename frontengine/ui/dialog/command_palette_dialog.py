"""Keyboard-accessible localized command search with recent/favorite commands."""
from __future__ import annotations

from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QPushButton, QVBoxLayout,
)

from frontengine.utils.actions.action_registry import Action, ActionRegistry
from frontengine.utils.actions.command_history import CommandHistory
from frontengine.utils.multi_language.retranslate import retranslator, tr, translate


class CommandPaletteDialog(QDialog):
    """Hide before executing so capture and overlay actions can take focus."""

    def __init__(self, registry: ActionRegistry, history: CommandHistory, parent=None) -> None:
        super().__init__(parent)
        self.registry, self.history = registry, history
        self.resize(620, 480)
        retranslator.bind(self, "command_palette_title", setter="setWindowTitle")
        layout = QVBoxLayout(self)
        self.search_input = QLineEdit()
        retranslator.bind(self.search_input, "command_palette_search", setter="setPlaceholderText")
        self.search_input.installEventFilter(self)
        self.results = QListWidget()
        self.value_input = QLineEdit()
        retranslator.bind(self.value_input, "command_palette_value", setter="setPlaceholderText")
        self.favorites_only = tr(QCheckBox(), "command_palette_favorites_only")
        self.run_button = tr(QPushButton(), "command_palette_run")
        self.favorite_button = tr(QPushButton(), "command_palette_favorite")
        self.run_button.setAutoDefault(False)
        self.favorite_button.setAutoDefault(False)
        self.status = QLabel()
        self.status.setWordWrap(True)
        for widget in (self.search_input, self.favorites_only, self.results, self.value_input, self.status):
            layout.addWidget(widget)
        buttons = QHBoxLayout()
        buttons.addWidget(self.favorite_button)
        buttons.addStretch()
        buttons.addWidget(self.run_button)
        layout.addLayout(buttons)
        self.search_input.textChanged.connect(self.refresh)
        self.favorites_only.toggled.connect(self.refresh)
        self.results.currentItemChanged.connect(self._selection_changed)
        self.results.itemActivated.connect(self.execute_selected)
        self.search_input.returnPressed.connect(self.execute_selected)
        self.value_input.returnPressed.connect(self.execute_selected)
        self.run_button.clicked.connect(self.execute_selected)
        self.favorite_button.clicked.connect(self.toggle_favorite)
        retranslator.bind_call(self.refresh)
        self.refresh()

    @staticmethod
    def _label(action: Action) -> str:
        return translate(action.label_key, action.fallback)

    def selected_id(self) -> str:
        """Return the selected stable ID, or an empty string for no match."""
        item = self.results.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else ""

    def refresh(self, *_args) -> None:
        """Re-evaluate current-language labels and keep the selected command."""
        selected = self.selected_id()
        known = set(self.registry.actions)
        favorites = self.history.values("favorites", known)
        recent = self.history.values("recent", known)
        actions = self.history.search(self.registry, self.search_input.text(), self._label,
                                      self.favorites_only.isChecked())
        self.results.clear()
        for action in actions:
            marker = "★ " if action.identifier in favorites else ""
            suffix = " · " + translate("command_palette_recent") if action.identifier in recent else ""
            item = QListWidgetItem(marker + self._label(action) + suffix)
            item.setData(Qt.ItemDataRole.UserRole, action.identifier)
            self.results.addItem(item)
            if action.identifier == selected:
                self.results.setCurrentItem(item)
        if self.results.currentRow() < 0 and self.results.count():
            self.results.setCurrentRow(0)
        self.status.setText("" if actions else translate("command_palette_empty"))
        self._selection_changed()

    def _selection_changed(self, *_args) -> None:
        action = self.registry.actions.get(self.selected_id())
        self.run_button.setEnabled(action is not None)
        self.favorite_button.setEnabled(action is not None)
        self.value_input.setVisible(bool(action and action.takes_value))

    def execute_selected(self, *_args) -> None:
        """Execute only registered commands, recording successful dispatch IDs."""
        identifier = self.selected_id()
        action = self.registry.actions.get(identifier)
        if action is None:
            return
        value = self.value_input.text().strip() if action.takes_value else ""
        if action.takes_value and not value:
            self.value_input.setFocus()
            return
        self.hide()
        try:
            if self.registry.execute(identifier, value):
                self.history.record(identifier, set(self.registry.actions))
        except (OSError, ValueError, RuntimeError) as error:
            self.show()
            self.status.setText(str(error))

    def toggle_favorite(self) -> None:
        """Persist the selected favorite without executing its action."""
        self.history.toggle_favorite(self.selected_id(), set(self.registry.actions))
        self.refresh()

    def eventFilter(self, watched, event) -> bool:
        if watched is self.search_input and event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down) and self.results.count():
                step = 1 if event.key() == Qt.Key.Key_Down else -1
                self.results.setCurrentRow((self.results.currentRow() + step) % self.results.count())
                return True
        return super().eventFilter(watched, event)

    def showEvent(self, event) -> None:
        self.value_input.clear()
        self.refresh()
        self.search_input.setFocus()
        self.search_input.selectAll()
        super().showEvent(event)
