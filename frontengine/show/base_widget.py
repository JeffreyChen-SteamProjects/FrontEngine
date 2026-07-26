from abc import abstractmethod
from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget

from frontengine.show.window_helpers import apply_overlay_window_flags, load_overlay_icon
from frontengine.user_setting.user_setting_file import get_overlay_geometry, save_overlay_geometry
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.power_mode.power_mode import DEFAULT_TIER, normalize_tier, tier_render_scale


class BaseWidget(QWidget):
    """
    BaseWidget: 提供共用 UI 屬性與事件處理的基底類別
    BaseWidget: Base class providing shared UI attributes and event handling
    """

    def __init__(self, draw_location_x: int = 0, draw_location_y: int = 0):
        super().__init__()
        self.draw_location_x: int = draw_location_x
        self.draw_location_y: int = draw_location_y
        self.opacity: float = 0.2
        # 鎖定＝點擊穿透；解鎖後可用拖曳擺位（見 window_helpers.set_overlay_locked）
        # Locked means click-through; unlocked overlays can be dragged into place.
        self.overlay_locked: bool = True
        self.overlay_lockable: bool = True
        self.overlay_show_on_bottom: bool = False
        # 綠幕背景色：設了就以不透明色填滿背景，方便 OBS 去背
        # Chroma key colour: fills the background opaquely so OBS can key it out.
        self.background_color: Optional[QColor] = None
        # 畫質檔位：影響更新頻率上限與算圖縮放（見 utils/power_mode）
        # Quality tier: caps the refresh rate and scales rendering (see utils/power_mode).
        self.quality_tier: str = DEFAULT_TIER
        # 分享畫面時要不要一起藏起來。遮蔽用的覆蓋層要留在畫面上——
        # 那正是它存在的理由，藏了就等於沒遮。
        # Whether this hides along with the others while sharing. A masking
        # overlay must stay visible in the capture: hiding it would defeat
        # the only thing it is for.
        self.keep_in_capture: bool = False
        self._drag_origin = None
        self._geometry_restored = False

        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        load_overlay_icon(self)

    def set_ui_window_flag(self, show_on_bottom: bool = False) -> None:
        front_engine_logger.info(f"{self.__class__.__name__} set_ui_window_flag | show_on_bottom: {show_on_bottom}")
        apply_overlay_window_flags(self, show_on_bottom=show_on_bottom)

    def set_ui_variable(self, opacity: float = 0.2) -> None:
        front_engine_logger.info(f"{self.__class__.__name__} set_ui_variable | opacity: {opacity}")
        self.opacity = opacity

    def set_quality_tier(self, tier: str) -> None:
        """
        設定畫質檔位。基底類別只記下來並通知子類別，實際怎麼省由子類別決定
        （例如放慢自己的計時器、用較低解析度算圖）。
        Set the quality tier. The base class records it and tells the subclass;
        what to actually give up - timer rate, render resolution - is the
        subclass's call.
        """
        self.quality_tier = normalize_tier(tier)
        front_engine_logger.info(
            f"{self.__class__.__name__} set_quality_tier | tier: {self.quality_tier}")
        self.apply_quality_tier()
        self.update()

    def apply_quality_tier(self) -> None:
        """子類別覆寫這裡，把新的檔位套到自己的計時器／算圖上。"""

    def render_scale(self) -> float:
        """目前檔位的算圖縮放，1.0 表示原生解析度。"""
        return tier_render_scale(self.quality_tier)

    def set_background_color(self, color) -> None:
        """
        設定綠幕背景色（傳 None 取消）。背景以不透明色填滿，內容再依原本的
        不透明度疊上去，這樣 OBS 的 Chroma Key 才能乾淨去背。
        Set the chroma key background colour (None clears it). The background is
        filled opaquely and the content drawn over it at the usual opacity, so
        OBS's chroma key filter can remove it cleanly.
        """
        if color is None:
            self.background_color = None
        else:
            candidate = QColor(color)
            self.background_color = candidate if candidate.isValid() else None
        self.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground, self.background_color is None)
        self.update()

    # --- drag to position (only while unlocked) --------------------------
    def mousePressEvent(self, event) -> None:
        if not self.overlay_locked and event.button() == Qt.MouseButton.LeftButton:
            self._drag_origin = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if not self.overlay_locked and self._drag_origin is not None:
            self.move(event.globalPosition().toPoint() - self._drag_origin)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._drag_origin is not None:
            self._drag_origin = None
            self.remember_geometry()
        super().mouseReleaseEvent(event)

    def remember_geometry(self) -> None:
        """記住目前位置與大小，之後同類覆蓋層會開在同一處。"""
        geometry = self.geometry()
        front_engine_logger.info(
            f"{self.__class__.__name__} remember_geometry | {geometry.x()},{geometry.y()} "
            f"{geometry.width()}x{geometry.height()}"
        )
        save_overlay_geometry(
            self.__class__.__name__, geometry.x(), geometry.y(), geometry.width(), geometry.height())

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self._geometry_restored:
            self._geometry_restored = True
            # 顯示流程結束後再套用，避免和 showFullScreen 打架
            # Applied after the show completes so it does not fight showFullScreen.
            QTimer.singleShot(0, self.restore_saved_geometry)

    def restore_saved_geometry(self) -> None:
        """若這類覆蓋層有記住的位置就套用（使用者拖曳過才會有）。"""
        saved = get_overlay_geometry(self.__class__.__name__)
        if not saved:
            return
        try:
            if self.isFullScreen():
                self.showNormal()
            self.setGeometry(*saved)
        except RuntimeError:  # pragma: no cover - widget closed mid-callback
            return

    def paintEvent(self, event) -> None:
        front_engine_logger.debug(f"{self.__class__.__name__} paintEvent | event: {event}")
        painter = QPainter(self)
        if self.background_color is not None:
            painter.fillRect(self.rect(), self.background_color)
        painter.save()
        painter.setOpacity(self.opacity)
        try:
            self.draw_content(painter)
        finally:
            painter.restore()

    @abstractmethod
    def draw_content(self, painter: QPainter) -> None:
        """Subclass hook that renders the widget content onto the shared painter."""
