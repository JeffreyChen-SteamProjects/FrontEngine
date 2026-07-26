"""
虛擬攝影機輸出：把螢幕上的一塊畫面（連同覆蓋層）當成一支 webcam 送出去，
讓 Zoom／Teams／Discord 直接選它當視訊來源。

需要系統上已經安裝虛擬攝影機驅動（OBS 的那支最常見）以及選用套件
`pyvirtualcam`。兩者缺一，available() 就是 False，整個功能維持關閉——
不會偷偷送出任何畫面。

Virtual camera output: send a region of the screen, overlays and all, as a
webcam that Zoom, Teams or Discord can pick as their video source.

It needs a virtual camera driver installed on the system - OBS's is the usual
one - and the optional `pyvirtualcam` package. Without either, available() is
False and the feature stays off; nothing is ever sent quietly.
"""
from __future__ import annotations

from typing import Any, Optional, Tuple

import numpy

from frontengine.utils.logging.loggin_instance import front_engine_logger

DEFAULT_WIDTH = 1280
DEFAULT_HEIGHT = 720
DEFAULT_FPS = 20
MIN_FPS = 5
MAX_FPS = 60
# 尺寸要是偶數：NV12 之類的格式以 2x2 為單位取樣，奇數會被驅動拒絕
# Sizes must be even: NV12 and friends sample in 2x2 blocks, and an odd size is
# rejected by the driver.
_SIZE_STEP = 2


def _module():
    """匯入 pyvirtualcam；沒安裝就回傳 None（這是預期情況，不是錯誤）。"""
    try:
        import pyvirtualcam

        return pyvirtualcam
    except ImportError:
        return None


def available() -> bool:
    """這台機器能不能輸出虛擬攝影機（有套件才算，驅動要等真的開才知道）。"""
    return _module() is not None


def clamp_fps(value: Any, fallback: int = DEFAULT_FPS) -> int:
    """每秒張數夾在驅動接受的範圍。"""
    try:
        return max(MIN_FPS, min(MAX_FPS, int(value)))
    except (TypeError, ValueError):
        return fallback


def even_size(width: Any, height: Any) -> Tuple[int, int]:
    """把尺寸調成偶數且不小於 2x2。"""
    def fix(value: Any, fallback: int) -> int:
        try:
            number = max(_SIZE_STEP, int(value))
        except (TypeError, ValueError):
            number = fallback
        return number - (number % _SIZE_STEP)

    return (fix(width, DEFAULT_WIDTH), fix(height, DEFAULT_HEIGHT))


def fit_frame(pixels: numpy.ndarray, width: int, height: int) -> numpy.ndarray:
    """
    把畫面調整成虛擬攝影機的尺寸：太大就等距取樣縮小，太小就補黑邊置中。
    虛擬攝影機的解析度在開啟時就固定了，之後每一張都必須剛好是那個大小。
    Fit a frame to the camera's size: sample it down when it is larger, and
    centre it on black when it is smaller. The resolution is fixed when the
    camera opens, so every frame afterwards has to match exactly.
    """
    target = numpy.zeros((height, width, 3), dtype=numpy.uint8)
    source = numpy.asarray(pixels, dtype=numpy.uint8)
    if source.ndim != 3 or source.shape[2] < 3 or source.size == 0:
        return target
    source = source[:, :, :3]
    source_height, source_width = source.shape[0], source.shape[1]
    scale = min(width / source_width, height / source_height, 1.0)
    draw_width = max(1, int(source_width * scale))
    draw_height = max(1, int(source_height * scale))
    rows = (numpy.linspace(0, source_height - 1, draw_height)).astype(numpy.int32)
    columns = (numpy.linspace(0, source_width - 1, draw_width)).astype(numpy.int32)
    resized = source[rows][:, columns]
    top = (height - draw_height) // 2
    left = (width - draw_width) // 2
    target[top:top + draw_height, left:left + draw_width] = resized
    return target


class VirtualCameraOutput:
    """
    開一支虛擬攝影機並持續送畫面。沒有套件或沒有驅動時 start() 回傳 False，
    並把原因記在 last_error 裡讓 UI 可以照實說明。
    Open a virtual camera and keep feeding it. Without the package or a driver,
    start() returns False and puts the reason in last_error so the UI can say
    what is actually wrong.
    """

    def __init__(self, width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT,
                 fps: int = DEFAULT_FPS) -> None:
        self.width, self.height = even_size(width, height)
        self.fps = clamp_fps(fps)
        self.last_error: str = ""
        self.frames_sent = 0
        self._camera = None

    @property
    def running(self) -> bool:
        return self._camera is not None

    @property
    def device(self) -> str:
        """正在使用的虛擬攝影機名稱；沒開就是空字串。"""
        return getattr(self._camera, "device", "") or "" if self._camera else ""

    def start(self) -> bool:
        """開啟虛擬攝影機。"""
        if self.running:
            return True
        module = _module()
        if module is None:
            self.last_error = "pyvirtualcam is not installed"
            front_engine_logger.info(f"[VirtualCamera] {self.last_error}")
            return False
        try:
            self._camera = module.Camera(width=self.width, height=self.height, fps=self.fps)
        except Exception as error:
            self._camera = None
            self.last_error = str(error)
            front_engine_logger.warning(f"[VirtualCamera] cannot open: {error!r}")
            return False
        self.last_error = ""
        self.frames_sent = 0
        front_engine_logger.info(
            f"[VirtualCamera] started | {self.device} {self.width}x{self.height}@{self.fps}")
        return True

    def stop(self) -> None:
        """關閉虛擬攝影機（其他程式那邊的畫面就會停住）。"""
        camera, self._camera = self._camera, None
        if camera is None:
            return
        try:
            camera.close()
        except Exception as error:  # pragma: no cover - driver boundary
            front_engine_logger.debug(f"[VirtualCamera] close failed: {error!r}")
        front_engine_logger.info(f"[VirtualCamera] stopped after {self.frames_sent} frame(s)")

    def send(self, pixels: Optional[numpy.ndarray]) -> bool:
        """送一張畫面出去（會先調整成攝影機的尺寸）。"""
        if not self.running or pixels is None:
            return False
        try:
            self._camera.send(fit_frame(pixels, self.width, self.height))
        except Exception as error:  # pragma: no cover - driver boundary
            self.last_error = str(error)
            front_engine_logger.warning(f"[VirtualCamera] send failed: {error!r}")
            return False
        self.frames_sent += 1
        return True
