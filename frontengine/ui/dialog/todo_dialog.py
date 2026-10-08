"""Local task editor and shared checkbox panel for the Today desktop widget."""
from datetime import date

from PySide6.QtCore import Qt, QDateTime, QTimer
from PySide6.QtWidgets import (QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
                              QPushButton, QCheckBox, QDateTimeEdit, QListWidget,
                              QListWidgetItem, QLabel, QFileDialog, QSizePolicy, QMessageBox)

from frontengine.utils.todo.calendar_import import display_time
from frontengine.utils.todo.repository import today_items
from frontengine.utils.multi_language.retranslate import tr, retranslator


class TodoPanel(QWidget):
    """Bounded plain-text checklist; every mutation goes through the durable worker."""

    def __init__(self, service, parent=None, *, editor: bool = True) -> None:
        super().__init__(parent)
        self.service, self.editor, self.refreshing = service, editor, False
        layout = QVBoxLayout(self)
        self.controls = []
        self.today = tr(QCheckBox(), 'todo_today_only')
        self.today.setChecked(not editor)
        self.today.toggled.connect(self.reload)
        layout.addWidget(self.today)
        if editor:
            self._build_editor(layout)
        self.entries = QListWidget()
        self.entries.itemChanged.connect(self._checked)
        layout.addWidget(self.entries, 1)
        self.status = tr(QLabel(), 'todo_hint' if editor else 'todo_today_hint')
        self.status.setWordWrap(True)
        self.status.setTextFormat(Qt.TextFormat.PlainText)
        self.status.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        self.status.setMinimumHeight(80 if editor else 60)
        layout.addWidget(self.status)
        self.service.result.connect(self._result)
        self.service.failed.connect(self._failed)
        self.service.started.connect(self._started)
        self.timer = QTimer(self)
        self.timer.setInterval(60000)
        self.timer.timeout.connect(self.reload)
        retranslator.bind_call(self.reload)

    def _build_editor(self, layout) -> None:
        self.title = QLineEdit()
        self.title.setMaxLength(1000)
        tr(self.title, 'todo_new_title', setter='setPlaceholderText')
        self.has_due = tr(QCheckBox(), 'todo_due')
        self.due = QDateTimeEdit(QDateTime.currentDateTime())
        self.due.setCalendarPopup(True)
        self.due.setDisplayFormat('yyyy-MM-dd HH:mm')
        row = QHBoxLayout()
        for widget in (self.title, self.has_due, self.due):
            row.addWidget(widget)
            self.controls.append(widget)
        layout.addLayout(row)
        row = QHBoxLayout()
        for key, callback in [('todo_add', self._add), ('todo_import', self._import),
                              ('todo_remove', self._remove), ('todo_clear', self._clear)]:
            button = tr(QPushButton(), key)
            button.clicked.connect(callback)
            row.addWidget(button)
            self.controls.append(button)
        layout.addLayout(row)

    def _request(self, action: str, **arguments) -> None:
        self.service.request(action, **arguments)

    def _started(self, _action: str) -> None:
        self._enabled(False)
        retranslator.set_text(self.status, 'todo_working')

    def _enabled(self, enabled: bool) -> None:
        for widget in [self.entries, *self.controls]:
            widget.setEnabled(enabled)

    def _add(self) -> None:
        if not self.title.text().strip():
            return
        due = None
        if self.has_due.isChecked():
            due = {'kind': 'utc', 'value': self.due.dateTime().toUTC().toPython().isoformat()}
            # PySide may return a naive datetime even for Qt::UTC.
            if not due['value'].endswith('+00:00'):
                due['value'] += '+00:00'
        self._request('add', title=self.title.text().strip(), due=due)

    def _import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, 'iCalendar', '', 'iCalendar (*.ics)')
        if path:
            self._request('import', path=path)

    def _remove(self) -> None:
        selected = self.entries.currentItem()
        if selected is not None:
            self._request('remove', id=selected.data(Qt.ItemDataRole.UserRole))

    def _clear(self) -> None:
        from frontengine.utils.multi_language.language_wrapper import language_wrapper
        text = language_wrapper.language_word_dict.get('todo_clear_confirm', 'Delete every task, event and cancellation record?')
        response = QMessageBox.question(self, self.windowTitle(), text,
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                        QMessageBox.StandardButton.No)
        if response == QMessageBox.StandardButton.Yes:
            self._request('clear')

    def _checked(self, item) -> None:
        if not self.refreshing:
            self._request('done', id=item.data(Qt.ItemDataRole.UserRole),
                          value=item.checkState() == Qt.CheckState.Checked)

    def _result(self, action: str, _items: list) -> None:
        if action == 'add' and self.editor:
            self.title.clear()
        self._enabled(True)
        retranslator.set_text(self.status, 'todo_hint' if self.editor else 'todo_today_hint')
        self.reload()

    def _failed(self, _action: str, reason: str) -> None:
        self._enabled(True)
        retranslator.forget(self.status)
        self.status.setText(reason)
        self.reload()

    def reload(self, *_args) -> None:
        """Rebuild at most 500 plain-text rows; all-day end dates are exclusive."""
        if not hasattr(self, 'entries'):
            return
        selected = self.entries.currentItem()
        identity = selected.data(Qt.ItemDataRole.UserRole) if selected is not None else None
        self.refreshing = True
        self.entries.clear()
        items = today_items(self.service.items, date.today()) if self.today.isChecked() else self.service.items
        for entry in items:
            moment = entry['start'] if entry['kind'] == 'event' else entry['due']
            label = entry['title'] + (' · ' + display_time(moment) if moment else '')
            item = QListWidgetItem(label)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if entry['done'] else Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, entry['id'])
            item.setToolTip(entry['description'])
            self.entries.addItem(item)
            if entry['id'] == identity:
                self.entries.setCurrentItem(item)
        self.refreshing = False

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.reload()
        if not self.service.loaded and not self.service.busy:
            self._request('load')
        self._enabled(not self.service.busy)
        self.timer.start()

    def hideEvent(self, event) -> None:
        self.timer.stop()
        super().hideEvent(event)

    def stop(self) -> None:
        """Stop local date polling while the owner closes."""
        self.timer.stop()


class TodoDialog(QDialog):
    """One reusable editor; task storage is independent of dialog visibility."""

    def __init__(self, service, parent=None) -> None:
        super().__init__(parent)
        tr(self, 'todo_title', setter='setWindowTitle')
        self.resize(760, 600)
        self.panel = TodoPanel(service, self)
        QVBoxLayout(self).addWidget(self.panel)

    def closeEvent(self, event) -> None:
        self.panel.stop()
        super().closeEvent(event)
