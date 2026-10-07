"""Today checklist overlay with an injected panel factory to preserve dependency direction."""
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QVBoxLayout

from frontengine.show.base_widget import BaseWidget
from frontengine.show.window_helpers import apply_overlay_window_flags


class TodoWidget(BaseWidget):
    """Keep today's events and overdue tasks visible; close stops panel date polling."""

    def __init__(self, panel_factory: Callable) -> None:
        super().__init__()
        self.overlay_lockable = False
        self.overlay_remembers_geometry = False
        self.opacity = 1.0
        self.closed = False
        self._requested_render_backend = 'software'
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        apply_overlay_window_flags(self, show_on_bottom=False, allow_input=True)
        self.resize(420, 460)
        self.panel = panel_factory(self)
        QVBoxLayout(self).addWidget(self.panel)

    def draw_content(self, painter) -> None:
        """Draw a neutral background under interactive checkbox children."""
        painter.fillRect(self.rect(), self.panel.palette().color(QPalette.ColorRole.Window))

    def set_render_backend(self, backend: str = 'auto') -> None:
        """Interactive children require ordinary Qt painting, with no covering compositor."""
        self._requested_render_backend = 'software'

    def closeEvent(self, event) -> None:
        self.closed = True
        self.panel.stop()
        super().closeEvent(event)
