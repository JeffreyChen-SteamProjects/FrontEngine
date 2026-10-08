"""Explicit monitor profile controls for already registered overlays."""
from PySide6.QtWidgets import QCheckBox, QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout
from frontengine.utils.multi_language.retranslate import tr, translate, retranslator


class MonitorProfilesDialog(QDialog):
    def __init__(self, service, parent=None, *, enabled_changed=None) -> None:
        super().__init__(parent)
        self.service = service
        tr(self, 'monitors_title', setter='setWindowTitle')
        self.resize(660, 290)
        layout = QVBoxLayout(self)
        self.hint = tr(QLabel(), 'monitors_hint')
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)
        self.auto = tr(QCheckBox(), 'monitors_auto')
        self.auto.setChecked(service.enabled)
        self.auto.toggled.connect(service.set_enabled)
        if enabled_changed:
            self.auto.toggled.connect(enabled_changed)
        layout.addWidget(self.auto)
        buttons = QHBoxLayout()
        for key, callback in (('monitors_save', service.save_current), ('monitors_restore', service.restore_current)):
            button = tr(QPushButton(), key)
            button.clicked.connect(lambda _checked=False, action=callback: self._run(action))
            buttons.addWidget(button)
        layout.addLayout(buttons)
        self.status = QLabel()
        self._count = None
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        service.changed.connect(self._changed)
        service.failed.connect(self.status.setText)
        retranslator.bind_call(self._refresh_status)

    def _run(self, callback) -> None:
        try:
            callback()
        except (ValueError, OSError, RuntimeError) as error:
            self.status.setText(str(error))

    def _changed(self, count: str) -> None:
        self._count = count
        self._refresh_status()

    def _refresh_status(self) -> None:
        if self._count is not None:
            self.status.setText(translate('monitors_result').format(count=self._count))
