import os
from pathlib import Path

from PySide6.QtCore import Qt, QRect
from PySide6.QtGui import QPainter, QFont, QIcon
from PySide6.QtWidgets import QWidget

from frontengine.utils.logging.loggin_instance import front_engine_logger


class TextWidget(QWidget):
    """
    TextWidget: 顯示文字的自訂元件
    TextWidget: A custom widget for displaying text
    """

    def __init__(self, text: str, draw_location_x: int = 0, draw_location_y: int = 0,
                 alignment: str = "Center"):
        """
        初始化文字元件
        Initialize text widget

        :param text: 要顯示的文字 / Text to display
        :param draw_location_x: 繪製位置 X / Drawing X coordinate
        :param draw_location_y: 繪製位置 Y / Drawing Y coordinate
        :param alignment: 對齊方式 / Alignment ("Center", "TopLeft", "TopRight", "BottomLeft", "BottomRight")
        """
        front_engine_logger.info(
            f"[TextWidget] Init | text={text}, x={draw_location_x}, y={draw_location_y}, alignment={alignment}"
        )
        super().__init__()

        # --- 基本屬性 / Basic attributes ---
        self.draw_location_x = draw_location_x
        self.draw_location_y = draw_location_y
        self.text = text
        self.font_size = 100
        self.opacity = 0.2

        # 設定透明背景 / Transparent background
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        # 設定對齊方式 / Set alignment
        self.set_alignment(alignment)

        # 預設字型 / Default font
        self.draw_font = QFont(self.font().family(), self.font_size)

        # 設定 Icon / Set window icon
        self.icon_path = Path(os.getcwd()) / "je_driver_icon.ico"
        if self.icon_path.exists() and self.icon_path.is_file():
            self.setWindowIcon(QIcon(str(self.icon_path)))

    def set_ui_window_flag(self, show_on_bottom: bool = False) -> None:
        """
        設定視窗旗標 (保持最上層或最下層)
        Set window flags (stay on top or bottom)
        """
        front_engine_logger.info(f"[TextWidget] set_ui_window_flag | show_on_bottom={show_on_bottom}")
        self.setWindowFlag(
            Qt.WindowType.WindowTransparentForInput |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        if not show_on_bottom:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnBottomHint)

    def set_font_variable(self, font_size: int = 100) -> None:
        """
        設定字型大小
        Set font size
        """
        front_engine_logger.info(f"[TextWidget] set_font_variable | font_size={font_size}")
        self.font_size = font_size
        self.draw_font = QFont(self.font().family(), self.font_size)

    def set_ui_variable(self, opacity: float = 0.2) -> None:
        """
        設定透明度
        Set opacity
        """
        front_engine_logger.info(f"[TextWidget] set_ui_variable | opacity={opacity}")
        self.opacity = opacity

    def set_alignment(self, alignment: str = "Center") -> None:
        """
        設定文字對齊方式
        Set text alignment
        """
        front_engine_logger.info(f"[TextWidget] set_alignment | alignment={alignment}")
        if alignment == "TopLeft":
            self.alignment = Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft
        elif alignment == "TopRight":
            self.alignment = Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight
        elif alignment == "BottomLeft":
            self.alignment = Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft
        elif alignment == "BottomRight":
            self.alignment = Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight
        else:
            self.alignment = Qt.AlignmentFlag.AlignCenter

    def paintEvent(self, event) -> None:
        """
        繪製文字
        Paint text
        """
        front_engine_logger.debug(f"[TextWidget] paintEvent | event={event}")
        painter = QPainter(self)
        painter.setFont(self.draw_font)
        painter.setPen(Qt.GlobalColor.black)
        painter.setOpacity(self.opacity)
        painter.drawText(
            QRect(self.draw_location_x, self.draw_location_y, self.width(), self.height()),
            int(self.alignment),
            self.text
        )

    def mousePressEvent(self, event) -> None:
        front_engine_logger.debug(f"[TextWidget] mousePressEvent | event={event}")
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        front_engine_logger.debug(f"[TextWidget] mouseDoubleClickEvent | event={event}")
        super().mouseDoubleClickEvent(event)

    def mouseGrabber(self) -> None:
        front_engine_logger.debug("[TextWidget] mouseGrabber")
        super().mouseGrabber()