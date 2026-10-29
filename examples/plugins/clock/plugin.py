"""API v1 page: shared batch lifecycle, bounded preset state and close cleanup."""
from datetime import datetime
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLineEdit
from PySide6.QtGui import QColor
from frontengine.show.base_widget import BaseWidget


class ClockOverlay(BaseWidget):
    def __init__(self, caption: str) -> None:
        super().__init__()
        self.caption = caption
        self.resize(300, 90)
        self.set_ui_window_flag()
        self.opacity = 1
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.update)

    def draw_content(self, painter) -> None:
        painter.setPen(QColor('white'))
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                         self.caption + '\n' + datetime.now().strftime('%H:%M:%S'))

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.timer.start()

    def hideEvent(self, event) -> None:
        self.timer.stop()
        super().hideEvent(event)

    def closeEvent(self, event) -> None:
        self.timer.stop()
        super().closeEvent(event)


class ClockPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.overlay_widgets: list[ClockOverlay] = []
        layout = QVBoxLayout(self)
        self.caption = QLineEdit('Clock')
        layout.addWidget(self.caption)
        button = QPushButton('Show clock')
        button.clicked.connect(self.open_clock)
        layout.addWidget(button)
        layout.addStretch()

    def open_clock(self) -> None:
        """Create only on explicit action; the host owns batch close and shutdown."""
        if len(self.overlay_widgets) >= 8:
            return
        widget = ClockOverlay(self.caption.text()[:100])
        self.overlay_widgets.append(widget)
        widget.destroyed.connect(lambda: self._remove(widget))
        widget.show()

    def _remove(self, widget: ClockOverlay) -> None:
        if widget in self.overlay_widgets:
            self.overlay_widgets.remove(widget)

    def get_state(self) -> dict:
        return {'caption': self.caption.text()[:100]}

    def set_state(self, state: dict) -> None:
        caption = state.get('caption', 'Clock')
        if not isinstance(caption, str) or len(caption) > 100:
            raise ValueError('Clock caption must be a string up to 100 characters')
        self.caption.setText(caption)

    def release_overlay_resources(self) -> None:
        """Optional reusable batch cleanup; no resources are held outside overlays here."""

    def shutdown(self) -> None:
        """Idempotent final cleanup also works when used without the FrontEngine host."""
        for widget in self.overlay_widgets[:]:
            try:
                widget.close()
            except RuntimeError:
                pass
        self.overlay_widgets.clear()


FRONTENGINE_TABS = {'Example clock': ClockPage}
