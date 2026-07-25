"""
桌布覆蓋層：在所有視窗底下播放圖片或動圖，可依系統音量脈動（音訊反應桌布），
並由播放清單定時換張。音量來源沿用寵物已經在用的系統峰值電表，只讀電表、
不擷取音訊內容。

A wallpaper layer: plays an image or animation beneath every window, optionally
pulsing with the system output level, with a playlist swapping it over time.
The level comes from the same meter the pet uses — a meter reading only, never
captured audio.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QRect, Qt, QTimer
from PySide6.QtGui import QMovie, QPainter, QPixmap

from frontengine.show.base_widget import BaseWidget
from frontengine.utils.audio_meter.audio_envelope import AudioEnvelope
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.power_mode.power_mode import tier_interval

_ANIMATED_SUFFIXES = (".gif", ".webp")
MIN_REACT_SCALE = 1.0
MAX_REACT_SCALE = 1.25


def react_scale(level, strength: int = 100) -> float:
    """
    把音量 (0~1) 換成桌布的縮放比例：安靜時 1.0，最大聲時最多放大 25%。
    strength 是效果強度百分比，0 代表完全不反應。
    Map an audio level to a wallpaper scale: 1.0 when quiet, up to +25% loud.
    """
    try:
        clamped = max(0.0, min(1.0, float(level)))
    except (TypeError, ValueError):
        return MIN_REACT_SCALE
    try:
        share = max(0, min(100, int(strength))) / 100.0
    except (TypeError, ValueError):
        share = 1.0
    return MIN_REACT_SCALE + (MAX_REACT_SCALE - MIN_REACT_SCALE) * clamped * share


class WallpaperWidget(BaseWidget):
    """
    桌布：顯示一張圖或一段動圖，位於所有視窗底下；可選擇隨系統音量脈動。
    """

    REACT_INTERVAL_MS = 33

    def __init__(self, media_path: str = "", audio_react: bool = False,
                 react_strength: int = 100) -> None:
        front_engine_logger.info(
            f"[WallpaperWidget] Init | path={media_path}, audio_react={audio_react}")
        super().__init__()
        self.opacity = 1.0
        self.media_path: Optional[Path] = None
        self._movie: Optional[QMovie] = None
        self._pixmap: Optional[QPixmap] = None
        self.audio_react = bool(audio_react)
        self.react_strength = max(0, min(100, int(react_strength)))
        self.scale = MIN_REACT_SCALE
        self._level_provider = None
        self._envelope = AudioEnvelope()
        self._react_timer = QTimer(self)
        self._react_timer.timeout.connect(self._update_scale)
        if media_path:
            self.set_media(media_path)

    def set_media(self, media_path: str) -> bool:
        """換一張桌布；載不起來時保留原本的並回傳 False。"""
        path = Path(media_path)
        if not path.is_file():
            front_engine_logger.warning(f"[WallpaperWidget] missing media: {path}")
            return False
        if path.suffix.lower() in _ANIMATED_SUFFIXES:
            movie = QMovie(str(path))
            if not movie.isValid():
                return False
            self._stop_movie()
            self._movie = movie
            self._pixmap = None
            movie.frameChanged.connect(self.update)
            movie.start()
        else:
            pixmap = QPixmap(str(path))
            if pixmap.isNull():
                return False
            self._stop_movie()
            self._pixmap = pixmap
            self._movie = None
        self.media_path = path
        self.update()
        return True

    def set_audio_level_provider(self, provider) -> None:
        """設定音量來源（回傳 0~1 或 None）。"""
        self._level_provider = provider
        self._envelope.reset()

    def set_audio_react(self, enabled: bool, strength: Optional[int] = None) -> None:
        """開關音訊反應並視需要調整強度。"""
        self.audio_react = bool(enabled)
        if strength is not None:
            self.react_strength = max(0, min(100, int(strength)))
        if self.audio_react:
            self._react_timer.start(tier_interval(self.REACT_INTERVAL_MS, self.quality_tier))
        else:
            self._react_timer.stop()
            self.scale = MIN_REACT_SCALE
            self.update()

    def apply_quality_tier(self) -> None:
        """畫質檔位改變時，跟著調整脈動的更新頻率（算圖縮放在繪製時套用）。"""
        if self._react_timer.isActive():
            self._react_timer.start(tier_interval(self.REACT_INTERVAL_MS, self.quality_tier))

    def _update_scale(self) -> None:
        """取一次音量、平滑後換成縮放比例。"""
        if not self.audio_react or self._level_provider is None:
            self.scale = MIN_REACT_SCALE
            return
        try:
            level = self._level_provider()
        except Exception:  # pragma: no cover - defensive around providers
            level = None
        if level is None:
            self.scale = MIN_REACT_SCALE
            self._envelope.reset()
        else:
            self.scale = react_scale(self._envelope.push(level), self.react_strength)
        self.update()

    def _stop_movie(self) -> None:
        if self._movie is not None:
            self._movie.stop()
            self._movie = None

    def current_pixmap(self) -> Optional[QPixmap]:
        if self._movie is not None:
            return self._movie.currentPixmap()
        return self._pixmap

    def draw_content(self, painter: QPainter) -> None:
        pixmap = self.current_pixmap()
        if pixmap is None or pixmap.isNull():
            return
        # 低畫質檔位先把來源縮小再放大回來：算的像素少，看起來只是稍軟。
        # Lower tiers shrink the source before scaling it back up: fewer pixels
        # to push, at the cost of a slightly softer picture.
        scale = self.render_scale()
        if scale < 1.0:
            pixmap = pixmap.scaled(
                max(1, int(pixmap.width() * scale)), max(1, int(pixmap.height() * scale)),
                Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.FastTransformation)
        width = int(self.width() * self.scale)
        height = int(self.height() * self.scale)
        # 放大時往外溢出，維持置中，畫面才不會出現黑邊
        # Overflow outward and stay centred so no bars appear while pulsing.
        painter.drawPixmap(
            QRect((self.width() - width) // 2, (self.height() - height) // 2, width, height), pixmap)

    def closeEvent(self, event) -> None:
        if self._react_timer.isActive():
            self._react_timer.stop()
        self._stop_movie()
        super().closeEvent(event)
