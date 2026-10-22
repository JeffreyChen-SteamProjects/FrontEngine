"""Preview and apply self-contained templates to an explicitly selected screen."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QComboBox, QDialog, QGraphicsScene, QGraphicsView, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QPushButton, QVBoxLayout,
)

from frontengine.ui.page.scene_setting.scene_visual_editor import SceneLayerItem
from frontengine.utils.multi_language.retranslate import retranslator, tr, translate
from frontengine.utils.scene_format.scene_templates import (
    BUILTIN_TEMPLATES, fit_template, missing_template_assets,
)


class SceneTemplatesDialog(QDialog):
    """Own only preview items; adoption belongs to the page's scene controller."""

    def __init__(self, page, *, templates=BUILTIN_TEMPLATES) -> None:
        super().__init__(page)
        self.page, self.templates = page, tuple(templates)
        self.pending = None
        self.setWindowTitle(translate('scene_templates'))
        self.resize(900, 620)
        self.list = QListWidget()
        self.list.setMaximumWidth(250)
        for template in self.templates:
            item = QListWidgetItem(translate(template.title_key))
            item.setData(Qt.ItemDataRole.UserRole, template.identifier)
            self.list.addItem(item)
        self.canvas = QGraphicsScene(self)
        self.view = QGraphicsView(self.canvas)
        self.view.setInteractive(False)
        self.description, self.status = QLabel(), QLabel()
        self.description.setWordWrap(True)
        self.status.setWordWrap(True)
        self._build_screen_choice()
        self._build_layout()
        self.list.currentRowChanged.connect(self._selection_changed)
        self.screen.currentIndexChanged.connect(self._selection_changed)
        retranslator.bind(self, 'scene_templates', setter='setWindowTitle')
        retranslator.bind_call(self._retranslate)
        if self.templates:
            self.list.setCurrentRow(0)

    def _build_screen_choice(self) -> None:
        self.screen = QComboBox()
        self.screen_targets = {}
        self.screen.addItem(translate('rules_screen_primary'), 'primary')
        for index, screen in enumerate(QGuiApplication.screens()):
            self.screen.addItem(f'{index}: {screen.name()}', index)
            self.screen_targets[index] = screen

    def _build_layout(self) -> None:
        layout = QVBoxLayout(self)
        hint = tr(QLabel(), 'template_hint')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        row = QHBoxLayout()
        row.addWidget(self.list)
        row.addWidget(self.view, 1)
        layout.addLayout(row, 1)
        layout.addWidget(self.description)
        screen_row = QHBoxLayout()
        screen_row.addWidget(tr(QLabel(), 'rules_scene_screen'))
        screen_row.addWidget(self.screen, 1)
        layout.addLayout(screen_row)
        layout.addWidget(self.status)
        self.apply_button = tr(QPushButton(), 'template_apply')
        self.apply_button.clicked.connect(self.apply_template)
        layout.addWidget(self.apply_button)

    def _selected(self):
        row = self.list.currentRow()
        return self.templates[row] if 0 <= row < len(self.templates) else None

    def _target_size(self) -> tuple[int, int]:
        selected = self.screen.currentData()
        screens = QGuiApplication.screens()
        if selected == 'primary':
            screen = QGuiApplication.primaryScreen()
        elif type(selected) is int and 0 <= selected < len(screens):
            screen = self.screen_targets.get(selected)
            if screen is not screens[selected]:
                raise ValueError('The selected template screen changed; reopen the library')
        else:
            raise ValueError('The selected template screen is unavailable')
        if screen is None:
            raise ValueError('No template screen is available')
        rectangle = screen.availableGeometry()
        return rectangle.width(), rectangle.height()

    def _selection_changed(self, *_args) -> None:
        self.canvas.clear()
        selected = self._selected()
        if selected is None:
            self.apply_button.setEnabled(False)
            return
        retranslator.set_text(self.description, selected.description_key)
        try:
            size = self._target_size()
            entries = fit_template(selected.entries(translate), size)
            missing = missing_template_assets(entries)
        except (OSError, ValueError) as error:
            self.status.setText(str(error))
            self.apply_button.setEnabled(False)
            return
        self.canvas.setSceneRect(0, 0, *size)
        for key, entry in entries.items():
            self.canvas.addItem(SceneLayerItem(self, key, entry))
        self.apply_button.setEnabled(not missing and self.pending is None)
        if missing:
            retranslator.forget(self.status)
            self.status.setText(translate('template_missing') + '\n' + '\n'.join(missing))
        else:
            retranslator.set_text(self.status, 'template_self_contained')
        self._fit()

    def _fit(self) -> None:
        self.view.fitInView(self.canvas.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def apply_template(self) -> None:
        """Revalidate the target before an atomic asynchronous scene replacement."""
        selected = self._selected()
        if selected is None or self.pending is not None:
            return
        try:
            entries = fit_template(selected.entries(translate), self._target_size())
            missing = missing_template_assets(entries)
            if missing:
                raise ValueError(translate('template_missing') + '\n' + '\n'.join(missing))
            self.pending = self.page.actions.request_entries(entries, self.screen.currentData())
        except (OSError, ValueError, RuntimeError) as error:
            self.status.setText(str(error))
            return
        self.pending.finished.connect(self._applied)
        self.apply_button.setEnabled(False)
        retranslator.set_text(self.status, 'scene_action_loading')

    def _applied(self, success: bool, error: str) -> None:
        self.pending = None
        self.apply_button.setEnabled(True)
        if success:
            self.page.tab_widget.setCurrentWidget(self.page.visual_editor)
            self.hide()
        else:
            retranslator.forget(self.status)
            self.status.setText(error)

    def _retranslate(self) -> None:
        for row, template in enumerate(self.templates):
            self.list.item(row).setText(translate(template.title_key))
        self.screen.setItemText(0, translate('rules_screen_primary'))
        self._selection_changed()

    def showEvent(self, event) -> None:
        self._selection_changed()
        super().showEvent(event)
        self._fit()

    def resizeEvent(self, event) -> None:
        self._fit()
        super().resizeEvent(event)

    def closeEvent(self, event) -> None:
        if self.pending is not None:
            self.page.actions.cancel_request(self.pending)
            self.pending = None
        self.canvas.clear()
        super().closeEvent(event)
