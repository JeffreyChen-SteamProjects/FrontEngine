"""Recorder adapter: asynchronous native start, latest Qt frame, explicit stop."""
from PySide6.QtCore import QObject, QRect, Qt, Signal
from PySide6.QtGui import QPixmap

from .capture import CaptureSession


class RegionCaptureAdapter(QObject):
    started = Signal()
    failed = Signal(str)

    def __init__(self, parent=None, session=None) -> None:
        super().__init__(parent)
        self.session = session or CaptureSession(self)
        self.region = QRect()
        if isinstance(self.session, QObject):
            self.session.started.connect(self.started, Qt.ConnectionType.QueuedConnection)
            self.session.failed.connect(self.failed, Qt.ConnectionType.QueuedConnection)

    def start(self, region: QRect) -> bool:
        self.region = QRect(region)
        if self.region.isEmpty():
            return False
        return self.session.start(region_rect=(region.x(), region.y(), region.width(), region.height()))

    def latest_frame(self, region: QRect | None = None):
        image = self.session.output_frame()
        if image.isNull():
            return None
        image.setDevicePixelRatio(1.0)
        if image.size() != self.region.size():
            image = image.scaled(self.region.size(), Qt.AspectRatioMode.IgnoreAspectRatio,
                                 Qt.TransformationMode.SmoothTransformation)
        return QPixmap.fromImage(image)

    def stop(self) -> None:
        self.session.stop()
