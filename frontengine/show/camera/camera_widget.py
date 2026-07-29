"""
攝影機覆蓋層：把本機攝影機的畫面放在桌面上（直播用的圓形頭像框那種）。
畫面只在本機顯示，不錄影、不上傳；關掉覆蓋層就停止擷取。

A camera overlay: put the local webcam on the desktop - the round talking-head
frame streamers use. The picture is shown locally only; nothing is recorded or
uploaded, and closing the overlay stops the camera.
"""
from __future__ import annotations

from typing import List, Optional, Tuple

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtMultimedia import QCamera, QMediaCaptureSession, QMediaDevices, QVideoSink

from frontengine.show.base_widget import BaseWidget
from frontengine.utils.logging.loggin_instance import front_engine_logger

SHAPE_RECTANGLE = "rectangle"
SHAPE_CIRCLE = "circle"
SHAPE_ROUNDED = "rounded"
SHAPES = (SHAPE_RECTANGLE, SHAPE_CIRCLE, SHAPE_ROUNDED)

DEFAULT_BORDER = 4
_CORNER_RADIUS = 18


def normalize_shape(shape) -> str:
    """把外框形狀正規化；不認得的一律當方形。"""
    name = str(shape or "").strip().lower()
    return name if name in SHAPES else SHAPE_RECTANGLE


def list_cameras() -> List[Tuple[str, str]]:
    """
    可用的攝影機 [(id, 顯示名稱)]；沒有裝置或查詢失敗回傳空清單。
    Available cameras as (id, description); [] when there are none.
    """
    try:
        return [(bytes(device.id()).decode("utf-8", "replace"), device.description())
                for device in QMediaDevices.videoInputs()]
    except Exception as error:  # pragma: no cover - depends on the platform backend
        front_engine_logger.warning(f"[CameraWidget] listing cameras failed: {error!r}")
        return []


def shape_path(shape: str, rect: QRect) -> QPainterPath:
    """外框形狀對應的裁切路徑。"""
    path = QPainterPath()
    name = normalize_shape(shape)
    if name == SHAPE_CIRCLE:
        size = min(rect.width(), rect.height())
        square = QRect(rect.x() + (rect.width() - size) // 2,
                       rect.y() + (rect.height() - size) // 2, size, size)
        path.addEllipse(square)
    elif name == SHAPE_ROUNDED:
        path.addRoundedRect(rect, _CORNER_RADIUS, _CORNER_RADIUS)
    else:
        path.addRect(rect)
    return path


class CameraWidget(BaseWidget):
    """
    攝影機畫面覆蓋層。影像來源可注入（測試直接餵 QPixmap），因此不需要真的
    攝影機也能驗證裁切與繪製。
    """

    def __init__(self, shape: str = SHAPE_CIRCLE, border: int = DEFAULT_BORDER,
                 mirrored: bool = True) -> None:
        front_engine_logger.info(f"[CameraWidget] Init | shape={shape}")
        super().__init__()
        self.opacity = 1.0
        self.shape = normalize_shape(shape)
        self.border = max(0, int(border))
        self.mirrored = bool(mirrored)
        self.border_color = QColor("#ffffff")
        self.frame: Optional[QPixmap] = None
        self._camera: Optional[QCamera] = None
        self._session: Optional[QMediaCaptureSession] = None
        self._sink: Optional[QVideoSink] = None
        self.resize(240, 240)

    def set_shape(self, shape: str) -> None:
        self.shape = normalize_shape(shape)
        self.update()

    def set_border(self, border: int) -> None:
        self.border = max(0, int(border))
        self.update()

    def set_mirrored(self, mirrored: bool) -> None:
        """自拍鏡像：看自己的時候左右相反比較自然。"""
        self.mirrored = bool(mirrored)
        self.update()

    def set_frame(self, pixmap: Optional[QPixmap]) -> None:
        """直接給一張畫面（正式由攝影機推送，測試直接餵）。"""
        self.frame = pixmap if pixmap is not None and not pixmap.isNull() else None
        self.update()

    def start(self, camera_id: Optional[str] = None) -> bool:
        """
        打開攝影機開始顯示；沒有裝置或啟動失敗回傳 False。
        Open the camera. False when there is no device or it refuses to start.
        """
        devices = QMediaDevices.videoInputs()
        if not devices:
            front_engine_logger.warning("[CameraWidget] no camera available")
            return False
        chosen = devices[0]
        if camera_id:
            for device in devices:
                if bytes(device.id()).decode("utf-8", "replace") == camera_id:
                    chosen = device
                    break
        try:
            self.stop()
            self._camera = QCamera(chosen)
            self._sink = QVideoSink(self)
            self._sink.videoFrameChanged.connect(self._on_frame)
            self._session = QMediaCaptureSession()
            self._session.setCamera(self._camera)
            self._session.setVideoSink(self._sink)
            self._camera.start()
        except Exception as error:  # pragma: no cover - depends on the backend
            front_engine_logger.warning(f"[CameraWidget] start failed: {error!r}")
            self.stop()
            return False
        front_engine_logger.info(f"[CameraWidget] started | {chosen.description()}")
        return True

    def stop(self) -> None:
        """關閉攝影機（覆蓋層關掉時一定會走到這裡）。"""
        if self._camera is not None:
            try:
                self._camera.stop()
            except RuntimeError:  # pragma: no cover - already torn down
                pass
        # sink 的 parent 是這個 widget，所以只把 Python 參考設成 None 不會銷毀它。
        # 每次重新 start()（例如換攝影機）都會多留一個還連著 _on_frame 的孤兒。
        # The sink is parented to this widget, so dropping the Python reference
        # does not destroy it: every restart - switching camera, say - leaves
        # another orphan still connected to _on_frame.
        if self._sink is not None:
            try:
                self._sink.deleteLater()
            except RuntimeError:  # pragma: no cover - already torn down
                pass
        self._camera = None
        self._session = None
        self._sink = None

    def _on_frame(self, video_frame) -> None:  # pragma: no cover - needs a real camera
        image = video_frame.toImage() if video_frame is not None else None
        if image is None or image.isNull():
            return
        self.set_frame(QPixmap.fromImage(image))

    def draw_content(self, painter: QPainter) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        path = shape_path(self.shape, self.rect())
        painter.save()
        painter.setClipPath(path)
        if self.frame is not None:
            scaled = self.frame.scaled(
                self.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation)
            if self.mirrored:
                scaled = scaled.transformed(_mirror_transform())
            painter.drawPixmap(
                QRect((self.width() - scaled.width()) // 2,
                      (self.height() - scaled.height()) // 2,
                      scaled.width(), scaled.height()), scaled)
        else:
            painter.fillRect(self.rect(), QColor(0, 0, 0, 160))
        painter.restore()
        if self.border > 0:
            painter.setPen(QPen(self.border_color, self.border))
            painter.drawPath(path)

    def closeEvent(self, event) -> None:
        self.stop()
        super().closeEvent(event)


def _mirror_transform():
    """左右翻轉用的變換矩陣。"""
    from PySide6.QtGui import QTransform

    return QTransform().scale(-1, 1)
