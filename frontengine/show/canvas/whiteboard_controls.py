"""Board-local page controls and asynchronous editable-file operations."""
from __future__ import annotations

from threading import Event
from copy import deepcopy
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox, QLabel, QFileDialog
from frontengine.utils.whiteboard.document import read_document, write_document
from frontengine.utils.whiteboard.raster import save_page
from frontengine.utils.multi_language.retranslate import tr, translate, retranslator


class _Result(QObject):
    done = Signal(str, object, str)


class _FileJob(QRunnable):
    def __init__(self, kind: str, function, result: _Result) -> None:
        super().__init__()
        self.kind, self.function, self.result = kind, function, result

    def run(self) -> None:
        result, error = None, ''
        try:
            result = self.function()
        except (OSError, ValueError, RecursionError) as failure:
            error = str(failure)
        try:
            self.result.done.emit(self.kind, result, error)
        except RuntimeError:
            pass


class WhiteboardControls(QWidget):
    """Own the file-worker boundary; board lifetime closes previews and cancels saves."""

    def __init__(self, board) -> None:
        super().__init__(board)
        self.board, self.closed, self.pending = board, False, None
        self.setAutoFillBackground(True)
        self.result = _Result(self)
        self.result.done.connect(self._done, Qt.ConnectionType.QueuedConnection)
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        file_row = QHBoxLayout()
        self.pages = QComboBox()
        self.pages.currentIndexChanged.connect(self._select_page)
        row.addWidget(self.pages)
        self.buttons = []
        for key, callback in [('board_page_add', self._add_page), ('board_page_remove', self._remove_page),
                              ('board_draw', lambda: self.board.set_select_mode(False)),
                              ('board_select', lambda: self.board.set_select_mode(True)),
                              ('board_delete', self.board.delete_selected), ('board_undo', self.board.undo),
                              ('board_file_save', self.save_file), ('board_file_open', self.open_file),
                              ('board_export', self.export_page)]:
            button = tr(QPushButton(), key)
            button.clicked.connect(callback)
            (file_row if key in ('board_file_save', 'board_file_open', 'board_export') else row).addWidget(button)
            self.buttons.append(button)
        layout.addLayout(row)
        layout.addLayout(file_row)
        self.status = tr(QLabel(), 'board_hint')
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.status)
        retranslator.bind_call(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        if self.closed:
            return
        self.pages.blockSignals(True)
        self.pages.clear()
        for index in range(len(self.board.document.pages)):
            self.pages.addItem(translate('board_page').format(number=index+1))
        self.pages.setCurrentIndex(self.board.document.current)
        self.pages.blockSignals(False)

    def _select_page(self, index: int) -> None:
        if index >= 0:
            self.board.select_page(index)

    def _add_page(self) -> None:
        try:
            self.board.add_page()
        except ValueError as error:
            self._error(str(error))

    def _remove_page(self) -> None:
        self.board.remove_page()

    def _error(self, text: str) -> None:
        retranslator.forget(self.status)
        self.status.setText(text)

    def open_file(self) -> None:
        """Read and validate on a worker; loading never replaces current pages on error."""
        path, _filter = QFileDialog.getOpenFileName(self, translate('board_file_open'), '', 'Whiteboard (*.fewhiteboard)')
        if path:
            self._start('open', lambda: read_document(path))

    def save_file(self) -> None:
        """Snapshot the GUI-owned pages before a cancellable atomic background save."""
        path, _filter = QFileDialog.getSaveFileName(self, translate('board_file_save'), 'board.fewhiteboard', 'Whiteboard (*.fewhiteboard)')
        if path:
            snapshot = self.board.document.snapshot()
            cancel = Event()
            self._start('save', lambda: write_document(snapshot, path, cancel=cancel), cancel)

    def export_page(self) -> None:
        """Export the active page on a worker; pan, zoom and selected outlines are excluded."""
        path, _filter = QFileDialog.getSaveFileName(self, translate('board_export'), 'board-page.png', 'PNG (*.png)')
        if path:
            page, cancel = deepcopy(self.board.document.page), Event()
            self._start('export', lambda: save_page(page, path, cancel=cancel), cancel)

    def _start(self, kind: str, function, cancel: Event | None = None) -> None:
        if self.pending is not None or self.closed:
            return
        self.pending = cancel or Event()
        self.pages.setEnabled(False)
        for button in self.buttons:
            button.setEnabled(False)
        retranslator.set_text(self.status, 'board_working')
        QThreadPool.globalInstance().start(_FileJob(kind, function, self.result))

    def _done(self, kind: str, value, error: str) -> None:
        self.pending = None
        if self.closed:
            return
        self.pages.setEnabled(True)
        for button in self.buttons:
            button.setEnabled(True)
        if error:
            self._error(error)
        elif kind == 'open':
            self.board.load_document(value)
            retranslator.set_text(self.status, 'board_loaded')
        else:
            retranslator.set_text(self.status, 'board_saved')

    def shutdown(self) -> None:
        """Ignore late results and request cancellation before owner destruction."""
        self.closed = True
        if self.pending is not None:
            self.pending.set()
