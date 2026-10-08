"""GUI sprite-pack mapping, movement preview and cancellable folder export."""
from __future__ import annotations

from pathlib import Path
from threading import Event

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Qt, Signal
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QLineEdit, QPushButton, QSpinBox, QComboBox, QFileDialog, QInputDialog

from frontengine.ui.dialog.pet_pack_preview import PetPackPreview
from frontengine.utils.pet_pack.pack_builder import PackDraft, STATES, missing_actions, validate_sprite, load_pack, export_pack
from frontengine.utils.multi_language.retranslate import tr, translate, retranslator


class _Signals(QObject):
    done = Signal(str, object, str)


class _PackJob(QRunnable):
    def __init__(self, kind: str, function, cancel: Event, signals: _Signals) -> None:
        super().__init__()
        self.kind, self.function, self.cancel, self.signals = kind, function, cancel, signals

    def run(self) -> None:
        value, error = None, ''
        try:
            value = self.function(self.cancel)
        except (OSError, ValueError, RecursionError) as failure:
            error = str(failure)
        try:
            self.signals.done.emit(self.kind, value, error)
        except RuntimeError:
            pass  # File staging cleanup completes independently of a closed owner.


class PetPackEditor(QDialog):
    """Creates sprite folders accepted by DesktopPetWidget and Workshop pet packs."""

    pack_selected = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        tr(self, 'pack_editor_title', setter='setWindowTitle')
        self.resize(820, 700)
        self.actions, self.paths = {}, {}
        self.pending, self.exported = None, None
        self.closed = False
        self.status_kind = 'missing'
        self.edit_controls = []
        self.signals = _Signals(self)
        self.signals.done.connect(self._job_done, Qt.ConnectionType.QueuedConnection)
        layout = QVBoxLayout(self)
        self.preview = PetPackPreview(self)
        self.preview.failed.connect(self._error)
        layout.addWidget(self.preview, 1)
        self._build_actions(layout)
        self._build_traits(layout)
        row = QHBoxLayout()
        self.job_buttons = []
        for key, callback in [('pack_editor_import', self.import_folder),
                              ('pack_editor_export', self.export_folder), ('pack_editor_use', self.use_export)]:
            button = tr(QPushButton(), key)
            button.clicked.connect(callback)
            row.addWidget(button)
            self.job_buttons.append(button)
        self.use_button = self.job_buttons[-1]
        self.use_button.setEnabled(False)
        cancel = tr(QPushButton(), 'pack_editor_cancel')
        cancel.clicked.connect(self.cancel_job)
        row.addWidget(cancel)
        layout.addLayout(row)
        self.status = tr(QLabel(), 'pack_editor_hint')
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.status)
        retranslator.bind_call(self._retranslate)

    def _build_actions(self, layout) -> None:
        grid = QGridLayout()
        for row, state in enumerate(STATES):
            grid.addWidget(tr(QLabel(), 'pack_state_' + state), row, 0)
            path = QLineEdit()
            path.setReadOnly(True)
            self.paths[state] = path
            grid.addWidget(path, row, 1)
            choose = tr(QPushButton(), 'pack_editor_choose')
            choose.clicked.connect(lambda checked=False, value=state: self.choose_action(value))
            clear = tr(QPushButton(), 'pack_editor_clear')
            clear.clicked.connect(lambda checked=False, value=state: self.clear_action(value))
            grid.addWidget(choose, row, 2)
            grid.addWidget(clear, row, 3)
            self.edit_controls.extend((choose, clear))
        layout.addLayout(grid)

    def _build_traits(self, layout) -> None:
        row = QHBoxLayout()
        self.name = QLineEdit('Sprite pet')
        self.name.setMaxLength(80)
        self.size_field, self.speed = QSpinBox(), QSpinBox()
        self.size_field.setRange(16, 512)
        self.size_field.setValue(128)
        self.speed.setRange(1, 10)
        self.speed.setValue(3)
        self.selected_state = QComboBox()
        for state in STATES:
            self.selected_state.addItem(translate('pack_state_' + state), state)
        for key, field in [('pack_editor_name', self.name), ('pet_size_label', self.size_field),
                           ('pet_speed_label', self.speed), ('pack_editor_preview', self.selected_state)]:
            row.addWidget(tr(QLabel(), key))
            row.addWidget(field)
        self.size_field.valueChanged.connect(self._reload_preview)
        self.speed.valueChanged.connect(self._reload_preview)
        self.selected_state.currentIndexChanged.connect(self._reload_preview)
        self.edit_controls.extend((self.name, self.size_field, self.speed, self.selected_state))
        layout.addLayout(row)

    def _retranslate(self) -> None:
        self.selected_state.blockSignals(True)
        for index, state in enumerate(STATES):
            self.selected_state.setItemText(index, translate('pack_state_' + state))
        self.selected_state.blockSignals(False)
        if self.status_kind == 'missing':
            self._missing()
        elif self.status_kind == 'exported':
            self.status.setText(translate('pack_editor_exported').format(path=self.exported))

    def draft(self) -> PackDraft:
        """Snapshot choices before a worker starts; later edits cannot change its inputs."""
        return PackDraft(dict(self.actions), self.name.text(), self.size_field.value(), self.speed.value())

    def choose_action(self, state: str) -> None:
        """Map an existing sprite file to one action, with explicit invalid-resource errors."""
        path, _filter = QFileDialog.getOpenFileName(self, translate('pack_editor_choose'), '', 'Sprites (*.gif *.webp *.png *.jpg *.jpeg)')
        if not path:
            return
        try:
            self.actions[state] = str(validate_sprite(path))
        except (OSError, ValueError) as error:
            self._error(str(error))
            return
        self.paths[state].setText(self.actions[state])
        self._reload_preview()

    def clear_action(self, state: str) -> None:
        """Remove one mapping; optional missing actions are shown as fallback warnings."""
        self.actions.pop(state, None)
        self.paths[state].clear()
        self._reload_preview()

    def _reload_preview(self, *_args) -> None:
        state = self.selected_state.currentData()
        self.preview.shutdown()
        if state in self.actions and not self.closed:
            try:
                self.preview.load(self.actions[state], self.size_field.value(), self.speed.value(), state)
            except (OSError, ValueError) as error:
                self._error(str(error))
                return
        self._missing()

    def _missing(self) -> None:
        if self.pending is not None or self.closed:
            return
        missing = ', '.join(translate('pack_state_' + state) for state in missing_actions(self.draft()))
        self.status_kind = 'missing'
        retranslator.forget(self.status)
        self.status.setText(translate('pack_editor_missing').format(actions=missing or translate('pack_editor_complete')))

    def import_folder(self) -> None:
        """Read a bounded legacy pack on the worker without changing current choices on failure."""
        folder = QFileDialog.getExistingDirectory(self, translate('pack_editor_import'))
        if folder:
            self._start_job('import', lambda cancel: load_pack(folder, cancel=cancel))

    def export_folder(self) -> None:
        """Export into a new named folder inside the explicitly chosen parent."""
        parent = QFileDialog.getExistingDirectory(self, translate('pack_editor_export'))
        if not parent:
            return
        name, accepted = QInputDialog.getText(self, translate('pack_editor_export'), translate('pack_editor_folder'), text='sprite-pet')
        if not accepted:
            return
        if not name.strip() or Path(name).name != name or name in ('.', '..'):
            self._error(translate('pack_editor_bad_folder'))
            return
        draft, destination = self.draft(), Path(parent) / name
        self._start_job('export', lambda cancel: export_pack(draft, destination, cancel=cancel))

    def _start_job(self, kind: str, function) -> None:
        if self.pending is not None:
            return
        self.pending = Event()
        for button in self.job_buttons + self.edit_controls:
            button.setEnabled(False)
        self.status_kind = 'working'
        retranslator.set_text(self.status, 'pack_editor_working')
        QThreadPool.globalInstance().start(_PackJob(kind, function, self.pending, self.signals))

    def _job_done(self, kind: str, value, error: str) -> None:
        self.pending = None
        for button in self.job_buttons + self.edit_controls:
            button.setEnabled(True)
        self.use_button.setEnabled(self.exported is not None)
        if self.closed:
            return
        if error:
            self._error(error)
        elif kind == 'import':
            self.actions = dict(value.actions)
            self.name.setText(value.name)
            self.size_field.setValue(value.size)
            self.speed.setValue(value.speed)
            for state, field in self.paths.items():
                field.setText(self.actions.get(state, ''))
            self._reload_preview()
        else:
            self.exported = value
            self.status_kind = 'exported'
            self.use_button.setEnabled(True)
            retranslator.forget(self.status)
            self.status.setText(translate('pack_editor_exported').format(path=value))

    def use_export(self) -> None:
        """Select the exported folder on the Pet page; spawning still needs Start."""
        if self.exported is not None:
            self.pack_selected.emit(self.exported)

    def _error(self, error: str) -> None:
        self.status_kind = 'error'
        retranslator.forget(self.status)
        self.status.setText(error)

    def cancel_job(self) -> None:
        """Request cancellation; completed filesystem work is never silently undone."""
        if self.pending is not None:
            self.pending.set()

    def showEvent(self, event) -> None:
        self.closed = False
        self._reload_preview()
        super().showEvent(event)

    def done(self, result: int) -> None:
        self.closed = True
        self.cancel_job()
        self.preview.shutdown()
        super().done(result)

    def closeEvent(self, event) -> None:
        self.closed = True
        self.cancel_job()
        self.preview.shutdown()
        super().closeEvent(event)
