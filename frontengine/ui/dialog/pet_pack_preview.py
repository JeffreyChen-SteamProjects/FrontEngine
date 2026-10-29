"""Sprite-only preview inside the editor; never spawn a desktop pet or stats."""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, QSize, Signal
from PySide6.QtGui import QImageReader, QMovie, QPainter
from PySide6.QtWidgets import QWidget

from frontengine.utils.pet_pack.pack_builder import validate_sprite


class PetPackPreview(QWidget):
    """Preview selected action and movement speed with bounded uncached frames."""

    failed = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumSize(360, 240)
        self.movie, self.image = None, None
        self.pet_size, self.speed, self.state = 128, 3, 'walk'
        self.position = 0
        self.direction = 1
        self.timer = QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self._tick)

    def load(self, path: str, size: int, speed: int, state: str) -> None:
        """Replace the current movie before opening another sprite resource."""
        self.shutdown()
        source = validate_sprite(path)
        self.pet_size, self.speed, self.state = size, speed, state
        self.position, self.direction = 0, 1
        reader = QImageReader(str(source))
        if reader.supportsAnimation():
            self.movie = QMovie(str(source), parent=self)
            self.movie.setCacheMode(QMovie.CacheMode.CacheNone)
            self.movie.setScaledSize(reader.size().scaled(QSize(512, 512), Qt.AspectRatioMode.KeepAspectRatio))
            self.movie.frameChanged.connect(lambda _index: self.update())
            self.movie.error.connect(lambda _error: self.failed.emit(self.movie.lastErrorString()))
        else:
            reader.setScaledSize(reader.size().scaled(QSize(512, 512), Qt.AspectRatioMode.KeepAspectRatio))
            self.image = reader.read()
        if self.isVisible():
            self.resume()
        self.update()

    def resume(self) -> None:
        """Start animation only when its preview pane is visible."""
        if self.movie is None and self.image is None:
            return
        if self.movie is not None:
            self.movie.start()
        self.timer.start()

    def _tick(self) -> None:
        if self.state == 'walk':
            bound = max(0, self.width() - min(self.pet_size, self.height()))
            self.position += self.speed * self.direction
            if not 0 <= self.position <= bound:
                self.position = max(0, min(bound, self.position))
                self.direction *= -1
        self.update()

    def paintEvent(self, event) -> None:
        image = self.movie.currentImage() if self.movie is not None else self.image
        painter = QPainter(self)
        painter.fillRect(self.rect(), self.palette().base())
        if image is not None and not image.isNull():
            size = min(self.pet_size, self.height(), self.width())
            fitted = image.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            x = min(self.position, max(0, self.width() - fitted.width())) if self.state == 'walk' else (self.width() - fitted.width()) // 2
            painter.drawImage(x, self.height() - fitted.height(), fitted)
        painter.end()

    def hideEvent(self, event) -> None:
        self.timer.stop()
        if self.movie is not None:
            self.movie.setPaused(True)
        super().hideEvent(event)

    def showEvent(self, event) -> None:
        self.resume()
        super().showEvent(event)

    def shutdown(self) -> None:
        """Release movies and timers on resource replacement or close."""
        self.timer.stop()
        if self.movie is not None:
            self.movie.stop()
            self.movie.deleteLater()
            self.movie = None
        self.image = None

    def closeEvent(self, event) -> None:
        self.shutdown()
        super().closeEvent(event)
