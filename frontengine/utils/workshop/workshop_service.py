"""Qt ownership for a lazy Steam session and manual callback pump."""
from PySide6.QtCore import QObject, QTimer, Signal

from frontengine.utils.steam.steam_runtime import SteamRuntime


class WorkshopService(QObject):
    """Drive native callbacks on the UI thread; never initialize at import."""
    event_received = Signal(object)
    availability_changed = Signal(bool, str)

    def __init__(self, parent=None, backend=None) -> None:
        super().__init__(parent)
        self.backend = backend or SteamRuntime()
        self.timer = QTimer(self)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self._poll)

    def start(self) -> bool:
        """Initialize on user demand and expose the precise availability reason."""
        available = self.backend.initialize()
        if available:
            self.timer.start()
        self.availability_changed.emit(available, self.backend.reason)
        return available

    def _poll(self) -> None:
        try:
            for event in self.backend.poll():
                self.event_received.emit(event)
        except (OSError, ValueError, RuntimeError) as error:
            self.stop()
            self.availability_changed.emit(False, str(error))

    def stop(self) -> None:
        """Stop callbacks before shutting down the native runtime."""
        self.timer.stop()
        self.backend.shutdown()
