"""One-shot completion receipt for actions that finish after dispatch."""
from PySide6.QtCore import QObject, Signal


class DeferredAction(QObject):
    """Report completion once; acceptance does not imply successful execution."""

    finished = Signal(bool, str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.result: bool | None = None
        self.error = ''

    def finish(self, success: bool, error: str = '') -> None:
        """Resolve this receipt exactly once, including cancellation/failure."""
        if self.result is None:
            self.result, self.error = success, error
            self.finished.emit(success, error)
