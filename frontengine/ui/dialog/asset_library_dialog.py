"""Static local library, organization and explicit reviewed reference repair."""
from copy import deepcopy
from pathlib import Path

from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                              QPushButton, QCheckBox, QListWidget, QListWidgetItem,
                              QAbstractItemView, QPlainTextEdit, QFileDialog, QMessageBox)

from frontengine.utils.multi_language.retranslate import tr, retranslator, translate


class AssetLibraryDialog(QDialog):
    """One MainUI-owned window; previews never execute a selected asset's native content."""

    def __init__(self, service, document, parent=None) -> None:
        super().__init__(parent)
        self.service, self.document = service, document
        self.plan, self.current_query, self.scene_applied = None, None, False
        self.last_references = None
        tr(self, 'assets_title', setter='setWindowTitle')
        self.resize(900, 750)
        layout = QVBoxLayout(self)
        self.search, self.favorites = QLineEdit(), tr(QCheckBox(), 'assets_favorites')
        self.search.setMaxLength(256)
        tr(self.search, 'assets_search', setter='setPlaceholderText')
        row = QHBoxLayout()
        row.addWidget(self.search)
        row.addWidget(self.favorites)
        layout.addLayout(row)
        self.entries = QListWidget()
        self.entries.setViewMode(QListWidget.ViewMode.IconMode)
        self.entries.setIconSize(QSize(240, 160))
        self.entries.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.entries.setWordWrap(True)
        self.entries.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.entries.currentItemChanged.connect(self._selected)
        layout.addWidget(self.entries, 1)
        self.tags, self.favorite = QLineEdit(), tr(QCheckBox(), 'assets_favorite')
        self.tags.setMaxLength(1312)
        tr(self.tags, 'assets_tags', setter='setPlaceholderText')
        row = QHBoxLayout()
        row.addWidget(self.tags)
        row.addWidget(self.favorite)
        layout.addLayout(row)
        self._build_actions(layout)
        self.references = QPlainTextEdit()
        self.references.setReadOnly(True)
        self.references.setMaximumHeight(110)
        layout.addWidget(self.references)
        self.status = tr(QLabel(), 'assets_hint')
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.status)
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(250)
        self.search_timer.timeout.connect(self.reload)
        self.search.textChanged.connect(lambda: self.search_timer.start())
        self.favorites.toggled.connect(self.reload)
        service.result.connect(self._result)
        service.failed.connect(self._failed)
        service.started.connect(self._started)
        retranslator.bind_call(self._language_changed)

    def _build_actions(self, layout) -> None:
        self.buttons = []
        row = QHBoxLayout()
        for key, action in [('assets_add', self._add), ('assets_add_pet', self._add_pet),
                            ('assets_save', self._save), ('assets_remove', self._remove),
                            ('assets_references', self._references), ('assets_relink', self._relink)]:
            button = tr(QPushButton(), key)
            button.clicked.connect(action)
            self.buttons.append(button)
            row.addWidget(button)
        layout.addLayout(row)

    def _entry(self):
        item = self.entries.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else None

    def _selected(self, *_args) -> None:
        entry = self._entry()
        self.tags.setText(', '.join(entry['tags']) if entry else '')
        self.favorite.setChecked(bool(entry and entry['favorite']))
        self.references.clear()
        self.last_references = None

    def reload(self, *_args) -> None:
        """Decode selected thumbnails off-thread; retain a query to reject stale search results."""
        query = (self.search.text().strip(), self.favorites.isChecked())
        if self.service.request('list', text=query[0], favorites=query[1]):
            self.current_query = query

    def _add(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, translate('assets_add'), '',
                                             'Assets (*.png *.jpg *.jpeg *.webp *.bmp *.gif *.puppet *.json *.fescene)')
        if path:
            self.service.request('add', path=path)

    def _add_pet(self) -> None:
        path = QFileDialog.getExistingDirectory(self, translate('assets_add_pet'))
        if path:
            self.service.request('add', path=path)

    def _save(self) -> None:
        entry = self._entry()
        if entry:
            self.service.request('edit', identity=entry['id'], tags=[tag.strip() for tag in self.tags.text().split(',') if tag.strip()],
                                 favorite=self.favorite.isChecked())

    def _remove(self) -> None:
        entry = self._entry()
        if entry:
            self.service.request('remove', identity=entry['id'])

    def _references(self) -> None:
        entry = self._entry()
        if entry:
            self.service.request('references', identity=entry['id'], scene=deepcopy(self.document.entries))

    def _relink(self) -> None:
        entry = self._entry()
        if not entry:
            return
        if entry['kind'] == 'pet':
            replacement = QFileDialog.getExistingDirectory(self, translate('assets_relink'))
        else:
            replacement, _ = QFileDialog.getOpenFileName(self, translate('assets_relink'))
        if replacement:
            self.service.request('plan', identity=entry['id'], replacement=replacement, scene=deepcopy(self.document.entries))

    def _started(self, _action: str) -> None:
        for button in [*self.buttons, self.tags, self.favorite, self.entries, self.search, self.favorites]:
            button.setEnabled(False)
        retranslator.set_text(self.status, 'assets_working')

    def _enable(self) -> None:
        for button in [*self.buttons, self.tags, self.favorite, self.entries, self.search, self.favorites]:
            button.setEnabled(True)

    def _result(self, action: str, value) -> None:
        self._enable()
        retranslator.set_text(self.status, 'assets_hint')
        if action == 'list':
            query = (self.search.text().strip(), self.favorites.isChecked())
            if self.current_query != query:
                self.reload()
            elif self.isVisible():
                self._show_entries(value)
        elif action == 'references':
            self._show_references(value)
        elif action == 'plan':
            self._review(value)
        elif action == 'commit':
            self.plan, self.scene_applied = None, False
            self.reload()
        elif self.isVisible():
            self.reload()

    def _show_entries(self, values: list) -> None:
        selected = self._entry()
        self.entries.clear()
        for entry in values:
            label = ('★ ' if entry['favorite'] else '') + Path(entry['path']).name[:80]
            label += '\n' + translate('assets_kind_' + entry['kind'], entry['kind'])
            label += (' · ' + ', '.join(entry['tags'])[:80] if entry['tags'] else '')
            item = QListWidgetItem(QIcon(QPixmap.fromImage(entry['thumbnail'])), label)
            item.setSizeHint(QSize(260, 230))
            item.setData(Qt.ItemDataRole.UserRole, {key: value for key, value in entry.items() if key != 'thumbnail'})
            item.setToolTip(entry['path'] + '\n' + ', '.join(entry['tags']) + ('\n' + entry['error'] if entry['error'] else ''))
            self.entries.addItem(item)
            if selected and selected['id'] == entry['id']:
                self.entries.setCurrentItem(item)

    def _show_references(self, values: list) -> str:
        self.last_references = values
        text = '\n'.join(('' if value['writable'] else translate('assets_readonly') + ' · ') +
                         (translate('assets_current_scene') if value['owner'] == 'Current scene' else value['owner']) +
                         ': ' + ', '.join(value['locations']) for value in values)
        self.references.setPlainText(text or translate('assets_no_references'))
        return text

    def _language_changed(self) -> None:
        if self.last_references is not None:
            self._show_references(self.last_references)
        if self.isVisible() and not self.service.busy:
            self.reload()

    def _review(self, plan: dict) -> None:
        if not self.isVisible():
            return
        text = self._show_references(plan['references'])
        reply = QMessageBox.question(self, translate('assets_relink'),
                                     translate('assets_confirm') + '\n' + plan['old'] + '\n→ ' + plan['new'] + '\n\n' + text,
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.commit_plan(plan)

    def commit_plan(self, plan: dict) -> None:
        """Apply current document first, then durable repair; restore it on worker failure."""
        if self.document.entries != plan['scene_before']:
            self._failed('plan', translate('assets_scene_changed'))
            return
        self.plan, self.scene_applied = plan, False
        if plan['scene_after'] != plan['scene_before']:
            self.document.replace(plan['scene_after'], 'Relink scene asset')
            self.scene_applied = True
        if not self.service.request('commit', plan=plan):
            self._failed('commit', translate('assets_working'))

    def _failed(self, action: str, reason: str) -> None:
        if action == 'commit' and self.plan is not None and self.scene_applied:
            if self.document.entries == self.plan['scene_after']:
                self.document.replace(self.plan['scene_before'], 'Restore failed asset repair')
            else:
                reason += '\n' + translate('assets_scene_changed')
        self.plan, self.scene_applied = None, False
        self._enable()
        retranslator.forget(self.status)
        self.status.setText(reason)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.reload()

    def abort_repair(self) -> None:
        """Restore an in-flight scene edit before MainUI destroys previews during shutdown."""
        self.service.stop()
        if self.plan is not None:
            self._failed('commit', translate('assets_cancelled'))

    def closeEvent(self, event) -> None:
        self.search_timer.stop()
        self.entries.clear()
        super().closeEvent(event)
