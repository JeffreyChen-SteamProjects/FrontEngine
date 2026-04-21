from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QPainter, QFont

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
        self.set_alignment(alignment)
        self.draw_font = QFont(self.font().family(), self.font_size)

    def set_font_variable(self, font_size: int = 100) -> None:
        front_engine_logger.info(f"[TextWidget] set_font_variable | font_size={font_size}")
        self.font_size = font_size
        self.draw_font = QFont(self.font().family(), self.font_size)

    def set_alignment(self, alignment: str = "Center") -> None:
        front_engine_logger.info(f"[TextWidget] set_alignment | alignment={alignment}")
        self.alignment = _ALIGNMENT_MAP.get(alignment, _ALIGNMENT_MAP["Center"])

    def draw_content(self, painter: QPainter) -> None:
        painter.setFont(self.draw_font)
        painter.setPen(Qt.GlobalColor.black)
        painter.drawText(
            QRect(self.draw_location_x, self.draw_location_y, self.width(), self.height()),
            int(self.alignment),
            self.text,
        )
