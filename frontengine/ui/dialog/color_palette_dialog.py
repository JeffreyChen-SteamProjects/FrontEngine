"""Named/grouped colors, recent samples and exact CSS/JSON export."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QFileDialog, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QStyledItemDelegate, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from frontengine.utils.multi_language.retranslate import retranslator, tr, translate


class SwatchDelegate(QStyledItemDelegate):
    """Paint an RGB chip after the theme so stylesheets cannot obscure the color."""

    def paint(self, painter, option, index) -> None:
        super().paint(painter, option, index)
        color = QColor(index.data(Qt.ItemDataRole.DisplayRole))
        if color.isValid():
            chip = QRect(option.rect.right() - 30, option.rect.center().y() - 9, 18, 18)
            painter.save()
            painter.fillRect(chip, color)
            painter.setPen(QColor("#eeeeee"))
            painter.drawRect(chip)
            painter.restore()


class ColorPaletteDialog(QDialog):
    """Edit persisted colors; closing hides this reusable management window."""

    def __init__(self, owner, palette) -> None:
        super().__init__(owner)
        self.owner, self.palette = owner, palette
        self.resize(760, 580)
        retranslator.bind(self, "palette_title", setter="setWindowTitle")
        layout = QVBoxLayout(self)
        self.search = QLineEdit()
        retranslator.bind(self.search, "palette_search", setter="setPlaceholderText")
        self.table = QTableWidget(0, 3)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setItemDelegateForColumn(2, SwatchDelegate(self.table))
        self.name_input, self.group_input, self.color_input = QLineEdit(), QLineEdit(), QLineEdit("#ffd740")
        self.recent = QComboBox()
        self.status = QLabel()
        self.status.setWordWrap(True)
        for widget, key in ((self.name_input, "palette_name"), (self.group_input, "palette_group"),
                            (self.color_input, "palette_color")):
            retranslator.bind(widget, key, setter="setPlaceholderText")
        new_row = QHBoxLayout()
        for widget in (self.name_input, self.group_input, self.color_input, self._button("palette_add", self.add)):
            new_row.addWidget(widget)
        buttons = QHBoxLayout()
        for widget in (self._button("palette_pick", self._start_pick),
                       self._button("palette_remove", self.remove),
                       self._button("palette_copy", self.copy_color),
                       self._button("palette_export_css", lambda: self.export("css")),
                       self._button("palette_export_json", lambda: self.export("json"))):
            buttons.addWidget(widget)
        layout.addWidget(self.search)
        layout.addWidget(self.table)
        layout.addLayout(new_row)
        layout.addWidget(tr(QLabel(), "palette_recent"))
        layout.addWidget(self.recent)
        layout.addLayout(buttons)
        layout.addWidget(self.status)
        self.search.textChanged.connect(self.refresh)
        self.table.cellChanged.connect(self._edit)
        self.recent.activated.connect(lambda _index: self.color_input.setText(self.recent.currentText()))
        retranslator.bind_call(self.refresh)
        self.refresh()

    def _button(self, key: str, callback) -> QPushButton:
        button = tr(QPushButton(), key)
        button.setAutoDefault(False)
        button.clicked.connect(callback)
        return button

    def refresh(self, *_args) -> None:
        """Render current swatches and samples without writing settings."""
        selected = self._selected_id()
        query = self.search.text().casefold().strip()
        entries = [entry for entry in self.palette.entries
                   if query in " ".join(entry[key] for key in ("name", "group", "color")).casefold()]
        self.table.blockSignals(True)
        self.table.setHorizontalHeaderLabels([translate("palette_" + key) for key in ("name", "group", "color")])
        self.table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            for column, key in enumerate(("name", "group", "color")):
                item = QTableWidgetItem(entry[key])
                item.setData(Qt.ItemDataRole.UserRole, entry["id"])
                if key == "color":
                    color = QColor(entry[key])
                    item.setBackground(color)
                    item.setForeground(QColor("#000000" if color.lightness() > 128 else "#ffffff"))
                self.table.setItem(row, column, item)
            if entry["id"] == selected:
                self.table.selectRow(row)
        self.table.blockSignals(False)
        self.recent.clear()
        self.recent.addItems(self.palette.recent)
        if self.palette.load_errors:
            self.status.setText(translate("palette_load_error").format(count=self.palette.load_errors))

    def _selected_id(self) -> str:
        row = self.table.currentRow()
        item = self.table.item(row, 0) if row >= 0 else None
        return item.data(Qt.ItemDataRole.UserRole) if item else ""

    def _apply(self, function) -> None:
        try:
            function()
            self.status.clear()
        except (OSError, ValueError) as error:
            self.status.setText(str(error))
        self.refresh()

    def add(self) -> None:
        """Validate and persist the new name/group/hex fields together."""
        self._apply(lambda: self.palette.add(self.name_input.text(), self.group_input.text(), self.color_input.text()))

    def _edit(self, row: int, _column: int) -> None:
        item = self.table.item(row, 0)
        if item is None or any(self.table.item(row, column) is None for column in range(3)):
            return
        identifier = item.data(Qt.ItemDataRole.UserRole)
        values = [self.table.item(row, column).text() for column in range(3)]
        self._apply(lambda: self.palette.update(identifier, *values))

    def remove(self) -> None:
        """Remove the selected swatch only."""
        identifier = self._selected_id()
        if identifier:
            self._apply(lambda: self.palette.remove(identifier))

    def copy_color(self) -> None:
        """Copy the stored exact hex value, independent of table edits."""
        from PySide6.QtGui import QGuiApplication
        entry = next((entry for entry in self.palette.entries if entry["id"] == self._selected_id()), None)
        clipboard = QGuiApplication.clipboard()
        if entry and clipboard is not None:
            clipboard.setText(entry["color"])

    def _start_pick(self) -> None:
        self.hide()
        self.owner.start_palette_pick()

    def export(self, format_name: str) -> None:
        """Export canonical values to the selected file with atomic replacement."""
        path, _ = QFileDialog.getSaveFileName(self, translate("palette_export_" + format_name), "",
                                             f"{format_name.upper()} (*.{format_name})")
        if path:
            self._apply(lambda: self.palette.export(Path(path), format_name))

    def showEvent(self, event) -> None:
        self.refresh()
        super().showEvent(event)
