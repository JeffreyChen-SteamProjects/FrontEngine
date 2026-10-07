"""Keep Qt alive while canceled local workers finish, without joining on the GUI thread."""
from collections.abc import Callable
from PySide6.QtCore import QObject, QTimer


class ShutdownBarrier(QObject):
    def __init__(self, pending: Callable[[], bool], finished: Callable[[], None], parent=None) -> None:
        super().__init__(parent)
        self.pending, self.finished = pending, finished
        self.done = False
        self.timer = QTimer(self)
        self.timer.setInterval(25)
        self.timer.timeout.connect(self.poll)

    def start(self) -> None:
        """Poll instead of blocking Qt image/font jobs behind application destruction."""
        if not self.done:
            self.timer.start()
            self.poll()

    def poll(self) -> None:
        if not self.done and not self.pending():
            self.done = True
            self.timer.stop()
            self.finished()
