from PySide6.QtCore import Qt, QRect, QTimer
from PySide6.QtGui import QPainter, QFont, QColor, QFontMetrics

from frontengine.show.base_widget import BaseWidget
from frontengine.utils.logging.loggin_instance import front_engine_logger


_ALIGNMENT_MAP = {
    "TopLeft": Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft,
    "TopRight": Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight,
    "BottomLeft": Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft,
    "BottomRight": Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight,
    "Center": Qt.AlignmentFlag.AlignCenter,
}


class TextWidget(BaseWidget):
    """
    TextWidget: 顯示文字的自訂元件
    TextWidget: A custom widget for displaying text
    """

    def __init__(self, text: str, draw_location_x: int = 0, draw_location_y: int = 0,
                 alignment: str = "Center"):
        front_engine_logger.info(
            f"[TextWidget] Init | text={text}, x={draw_location_x}, y={draw_location_y}, alignment={alignment}"
        )
        super().__init__(draw_location_x, draw_location_y)
        self.text = text
        self.font_size = 100
        self.pen_color: QColor = QColor(Qt.GlobalColor.black)
        self.outline: bool = False
        self.outline_color: QColor = QColor(Qt.GlobalColor.white)
        self.set_alignment(alignment)
        self.draw_font = QFont(self.font().family(), self.font_size)

        # Marquee (horizontal scroll) state
        self.marquee: bool = False
        self.marquee_speed: int = 4
        self.marquee_offset: int = 0
        self._marquee_timer = QTimer(self)
        self._marquee_timer.timeout.connect(self._tick_marquee)

        # 動態文字來源（時鐘／倒數／系統資訊…）/ Dynamic text source
        self.text_source = None
        self._source_timer = QTimer(self)
        self._source_timer.timeout.connect(self.refresh_text)

    def set_font_variable(self, font_size: int = 100) -> None:
        front_engine_logger.info(f"[TextWidget] set_font_variable | font_size={font_size}")
        self.font_size = font_size
        self.draw_font = QFont(self.draw_font.family(), self.font_size)

    def set_font_family(self, family: str) -> None:
        front_engine_logger.info(f"[TextWidget] set_font_family | family={family}")
        if family:
            self.draw_font = QFont(family, self.font_size)

    def set_color(self, color: str) -> None:
        front_engine_logger.info(f"[TextWidget] set_color | color={color}")
        candidate = QColor(color)
        if candidate.isValid():
            self.pen_color = candidate

    def set_outline(self, enabled: bool, color: str = None) -> None:
        front_engine_logger.info(f"[TextWidget] set_outline | enabled={enabled}, color={color}")
        self.outline = bool(enabled)
        if color is not None:
            candidate = QColor(color)
            if candidate.isValid():
                self.outline_color = candidate

    def set_alignment(self, alignment: str = "Center") -> None:
        front_engine_logger.info(f"[TextWidget] set_alignment | alignment={alignment}")
        self.alignment = _ALIGNMENT_MAP.get(alignment, _ALIGNMENT_MAP["Center"])

    def set_marquee(self, enabled: bool, speed: int = 4) -> None:
        front_engine_logger.info(f"[TextWidget] set_marquee | enabled={enabled}, speed={speed}")
        self.marquee = bool(enabled)
        try:
            self.marquee_speed = max(1, int(speed))
        except (TypeError, ValueError):
            self.marquee_speed = 4
        if self.marquee:
            self.marquee_offset = self.width()
            self._marquee_timer.start(30)
        else:
            self._marquee_timer.stop()

    def set_text_source(self, source) -> None:
        """
        接上動態文字來源（TextSource）；靜態來源只取一次文字，不啟動計時器。
        Attach a dynamic text source; a static one is read once, with no timer.
        """
        front_engine_logger.info(f"[TextWidget] set_text_source | kind={getattr(source, 'kind', None)}")
        self._source_timer.stop()
        self.text_source = source
        if source is None:
            return
        source.start()
        self.refresh_text()
        interval = getattr(source, "refresh_interval_ms", 0)
        if interval > 0:
            self._source_timer.start(int(interval))

    def refresh_text(self) -> None:
        """向來源取一次最新文字並重繪 / Pull the latest text and repaint."""
        if self.text_source is None:
            return
        try:
            text = self.text_source.text()
        except Exception as error:  # pragma: no cover - defensive around providers
            front_engine_logger.warning(f"[TextWidget] text source failed: {error!r}")
            return
        if text != self.text:
            self.text = text
            self.update()

    def _tick_marquee(self) -> None:
        text_width = QFontMetrics(self.draw_font).horizontalAdvance(self.text)
        self.marquee_offset -= self.marquee_speed
        if self.marquee_offset < -text_width:
            self.marquee_offset = self.width()
        self.update()

    def _draw_text(self, painter: QPainter, dx: int, dy: int) -> None:
        """在偏移 (dx, dy) 處繪製文字（供描邊重複繪製使用）。"""
        if self.marquee:
            metrics = painter.fontMetrics()
            baseline_y = self.draw_location_y + self.height() // 2 + metrics.ascent() // 2
            painter.drawText(self.draw_location_x + self.marquee_offset + dx, baseline_y + dy, self.text)
        else:
            painter.drawText(
                QRect(self.draw_location_x + dx, self.draw_location_y + dy, self.width(), self.height()),
                int(self.alignment),
                self.text,
            )

    def closeEvent(self, event) -> None:
        for timer in (self._marquee_timer, self._source_timer):
            if timer.isActive():
                timer.stop()
        super().closeEvent(event)

    def draw_content(self, painter: QPainter) -> None:
        painter.setFont(self.draw_font)
        if self.outline:
            painter.setPen(self.outline_color)
            for dx, dy in ((-2, -2), (-2, 0), (-2, 2), (0, -2), (0, 2), (2, -2), (2, 0), (2, 2)):
                self._draw_text(painter, dx, dy)
        painter.setPen(self.pen_color)
        self._draw_text(painter, 0, 0)
