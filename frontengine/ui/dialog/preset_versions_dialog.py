"""Preview actual preset settings with cancellation and transactional restore."""
from __future__ import annotations

from copy import deepcopy
from typing import Callable

from PySide6.QtWidgets import (
    QComboBox, QDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QPlainTextEdit, QVBoxLayout,
)
from PySide6.QtCore import Qt

from frontengine.user_setting.preset_history import compare_states
from frontengine.user_setting.preset_repository import PresetRepository
from frontengine.utils.multi_language.retranslate import retranslator, tr, translate


class PresetVersionsDialog(QDialog):
    """Configuration snapshots reference existing media; no media is duplicated."""

    def __init__(self, repository: PresetRepository, collect: Callable[[], dict],
                 apply: Callable[[dict], None], parent=None) -> None:
        super().__init__(parent)
        self.repository, self.collect, self.apply = repository, collect, apply
        self._baseline = None
        self.resize(760, 550)
        retranslator.bind(self, "preset_versions_title", setter="setWindowTitle")
        layout = QVBoxLayout(self)
        self.presets = QComboBox()
        self.versions = QListWidget()
        self.diff = QPlainTextEdit()
        self.diff.setReadOnly(True)
        self.hint = tr(QLabel(), "preset_versions_hint")
        self.hint.setWordWrap(True)
        self.status = QLabel()
        self.status.setWordWrap(True)
        for widget in (self.presets, self.hint, self.versions, self.diff, self.status):
            layout.addWidget(widget)
        row = QHBoxLayout()
        self.preview_button = tr(QPushButton(), "preset_versions_preview")
        self.cancel_button = tr(QPushButton(), "preset_versions_cancel")
        self.restore_button = tr(QPushButton(), "preset_versions_restore")
        for button in (self.preview_button, self.cancel_button, self.restore_button):
            button.setAutoDefault(False)
            row.addWidget(button)
        layout.addLayout(row)
        self.presets.currentTextChanged.connect(self._load_versions)
        self.versions.currentItemChanged.connect(self._selection_changed)
        self.preview_button.clicked.connect(self.preview_selected)
        self.cancel_button.clicked.connect(self.cancel_preview)
        self.restore_button.clicked.connect(self.restore_selected)
        self._selection_changed()

    def reload_presets(self) -> None:
        """Refresh names without losing an outstanding preview baseline."""
        if not self.cancel_preview():
            return
        selected = self.presets.currentText()
        self.presets.blockSignals(True)
        self.presets.clear()
        self.presets.addItems(self.repository.list_presets())
        index = self.presets.findText(selected)
        self.presets.setCurrentIndex(max(0, index))
        self.presets.blockSignals(False)
        self._load_versions()

    def _load_versions(self, *_args) -> None:
        if not self.cancel_preview():
            return
        self.versions.clear()
        name = self.presets.currentText()
        if not name:
            return
        try:
            history = self.repository.history(name)
            history.snapshot(self.repository.load(name))
            history.prune()
            for identifier, created in history.versions():
                item = QListWidgetItem(created + " · " + identifier[:12])
                item.setData(Qt.ItemDataRole.UserRole, identifier)
                self.versions.addItem(item)
            self.versions.setCurrentRow(0)
        except (OSError, ValueError) as error:
            self.status.setText(str(error))

    def _candidate(self) -> dict:
        item = self.versions.currentItem()
        if item is None:
            raise ValueError(translate("preset_versions_select"))
        return self.repository.history(self.presets.currentText()).load(item.data(Qt.ItemDataRole.UserRole))

    def _selection_changed(self, *_args) -> None:
        selected = self.versions.currentItem() is not None
        self.preview_button.setEnabled(selected)
        self.restore_button.setEnabled(selected)
        self.cancel_button.setEnabled(self._baseline is not None)
        self.diff.clear()
        if selected:
            try:
                original = self._baseline if self._baseline is not None else self.collect()
                self.diff.setPlainText(compare_states(original, self._candidate()))
            except (OSError, ValueError) as error:
                self.status.setText(str(error))

    def preview_selected(self) -> None:
        """Apply the exact candidate to pages until cancelled or restored."""
        try:
            candidate = self._candidate()
            if not self.cancel_preview():
                return
            baseline = deepcopy(self.collect())
            self.apply(candidate)
            self._baseline = baseline
            self.status.setText(translate("preset_versions_previewing"))
            self._selection_changed()
        except (OSError, ValueError, RuntimeError) as error:
            self.status.setText(str(error))

    def cancel_preview(self) -> bool:
        """Restore the original page configuration, including on close."""
        if self._baseline is not None:
            try:
                self.apply(self._baseline)
            except (OSError, ValueError, RuntimeError) as error:
                self.status.setText(str(error))
                return False
            self._baseline = None
        self.status.clear()
        self.cancel_button.setEnabled(False)
        return True

    def restore_selected(self) -> None:
        """Commit only after application succeeds; failed saves roll pages back."""
        try:
            candidate = self._candidate()
            if not self.cancel_preview():
                return
            original = deepcopy(self.collect())
            self.apply(candidate)
            try:
                self.repository.save(self.presets.currentText(), candidate)
            except (OSError, ValueError):
                self.apply(original)
                raise
            self._load_versions()
            self.status.setText(translate("preset_versions_restored"))
        except (OSError, ValueError, RuntimeError) as error:
            self.status.setText(str(error))

    def reject(self) -> None:
        self.close()

    def closeEvent(self, event) -> None:
        if self.cancel_preview():
            super().closeEvent(event)
        else:
            event.ignore()
