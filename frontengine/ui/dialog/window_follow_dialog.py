"""Choose an existing registered overlay and an explicit native target."""
import weakref

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton, QLabel

from frontengine.utils.window_pin.window_pin import list_windows
from frontengine.utils.multi_language.retranslate import tr, retranslator


class WindowFollowDialog(QDialog):
    """Temporary bindings only; no target handles are persisted or guessed on restart."""

    def __init__(self, service, provider, parent=None, *, lister=list_windows) -> None:
        super().__init__(parent)
        self.service, self.provider, self.lister = service, provider, lister
        tr(self, 'follow_title', setter='setWindowTitle')
        self.resize(640, 300)
        layout = QVBoxLayout(self)
        self.overlays, self.targets = QComboBox(), QComboBox()
        for key, widget in [('follow_overlay', self.overlays), ('follow_target', self.targets)]:
            row = QHBoxLayout()
            row.addWidget(tr(QLabel(), key))
            row.addWidget(widget, 1)
            layout.addLayout(row)
        row = QHBoxLayout()
        self.buttons = []
        for key, callback in [('follow_refresh', self.reload), ('follow_bind', self._bind), ('follow_detach', self._detach)]:
            button = tr(QPushButton(), key)
            button.clicked.connect(callback)
            row.addWidget(button)
            self.buttons.append(button)
        layout.addLayout(row)
        self.status = tr(QLabel(), 'follow_hint' if service.backend.available() else 'follow_unsupported')
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.status)
        self.buttons[1].setEnabled(service.backend.available())
        service.failed.connect(self._failed)

    def reload(self) -> None:
        """List only registered top-level overlays and current target windows."""
        self.overlays.clear()
        self.targets.clear()
        found = set()
        for widgets in self.provider():
            for widget in widgets:
                try:
                    if id(widget) in found or not widget.isWindow():
                        continue
                    found.add(id(widget))
                    label = widget.__class__.__name__ + (' · ' + widget.windowTitle()[:100] if widget.windowTitle() else '')
                    self.overlays.addItem(label, weakref.ref(widget))
                except (AttributeError, RuntimeError):
                    continue
        if self.service.backend.available():
            for handle, title in (self.lister() or [])[:200]:
                self.targets.addItem(str(title)[:200], int(handle))

    def _overlay(self):
        reference = self.overlays.currentData()
        return reference() if reference is not None else None

    def _bind(self) -> None:
        widget, handle = self._overlay(), self.targets.currentData()
        if widget is None or handle is None:
            return
        try:
            self.service.bind(widget, handle)
            retranslator.set_text(self.status, 'follow_bound')
        except (ValueError, OSError, RuntimeError) as error:
            self._failed(str(error))

    def _detach(self) -> None:
        widget = self._overlay()
        if widget is not None:
            self.service.unbind(widget)
            retranslator.set_text(self.status, 'follow_hint')

    def _failed(self, reason: str) -> None:
        retranslator.forget(self.status)
        self.status.setText(reason)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.reload()
