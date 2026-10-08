"""Read-only platform prerequisites and adapter failures; never enables capture."""
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem
from frontengine.utils.platform_info.capabilities import platform_capabilities
from frontengine.utils.multi_language.retranslate import tr, translate, retranslator


class PlatformCapabilitiesDialog(QDialog):
    def __init__(self, parent=None, *, provider=platform_capabilities) -> None:
        super().__init__(parent)
        self.provider = provider
        tr(self, 'platform_title', setter='setWindowTitle')
        self.resize(860, 420)
        layout = QVBoxLayout(self)
        hint = tr(QLabel(), 'platform_hint')
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.table = QTableWidget(0, 3)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table)
        button = tr(QPushButton(), 'follow_refresh')
        button.clicked.connect(self.refresh)
        layout.addWidget(button)
        retranslator.bind_call(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        """Expose original adapter error text next to localized capability/status names."""
        self.table.setHorizontalHeaderLabels([translate(key) for key in
                                              ('platform_capability', 'platform_status', 'platform_reason')])
        rows = self.provider()
        self.table.setRowCount(len(rows))
        for index, (name, available, reason) in enumerate(rows):
            values = (translate('platform_' + name), translate('platform_ready' if available else 'platform_unavailable'), reason)
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setToolTip(value)
                self.table.setItem(index, column, item)
        self.table.setColumnWidth(0, 140)
        self.table.setColumnWidth(1, 150)
        self.table.setColumnWidth(2, 510)
        self.table.resizeRowsToContents()
