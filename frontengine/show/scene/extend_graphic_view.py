from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import QGraphicsView

from frontengine.utils.logging.loggin_instance import front_engine_logger


class ExtendGraphicView(QGraphicsView):
    """
    ExtendGraphicView: 自訂 QGraphicsView，支援透明背景與滑鼠滾輪縮放
    ExtendGraphicView: Custom QGraphicsView with transparent background and wheel zoom
    """

    def __init__(self, *args):
        """
        初始化 ExtendGraphicView
        Initialize ExtendGraphicView
        """
        front_engine_logger.info(f"[ExtendGraphicView] Init | args={args}")
        super().__init__(*args)

        # 設定視窗旗標 / Set window flags
        self.setWindowFlag(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )

        # 設定透明背景 / Transparent background
        self.setStyleSheet("background:transparent")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        # 關閉捲軸 / Disable scrollbars
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # 設定拖曳模式 / Enable drag mode
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

    def wheelEvent(self, event) -> None:
        """
        滑鼠滾輪事件：支援縮放功能
        Mouse wheel event: supports zoom in/out
        """
        if not self.scene() or len(self.scene().items()) == 0:
            return

        front_engine_logger.debug(f"[ExtendGraphicView] wheelEvent | event={event}")

        # --- 計算滑鼠位置與場景座標 / Calculate mouse position and scene coordinates ---
        current_position = event.position()
        scene_position = self.mapToScene(QPoint(int(current_position.x()), int(current_position.y())))

        view_width = self.viewport().width()
        view_height = self.viewport().height()
        horizon_scale = current_position.x() / view_width
        vertical_scale = current_position.y() / view_height

        wheel_value = event.angleDelta().y()
        scale_factor = self.transform().m11()  # 當前縮放比例 / Current scale factor

        # --- 限制縮放範圍 / Limit zoom range ---
        if (scale_factor < 0.5 and wheel_value < 0) or (scale_factor > 50 and wheel_value > 0):
            return

        # --- 縮放操作 / Apply zoom ---
        zoom_in_factor = 1.2
        if wheel_value > 0:
            self.scale(zoom_in_factor, zoom_in_factor)
        else:
            self.scale(1.0 / zoom_in_factor, 1.0 / zoom_in_factor)

        # --- 調整視口位置，保持滑鼠位置對應場景點不變 / Adjust viewport to keep mouse focus ---
        view_point = self.transform().map(scene_position)
        self.horizontalScrollBar().setValue(int(view_point.x() - view_width * horizon_scale))
        self.verticalScrollBar().setValue(int(view_point.y() - view_height * vertical_scale))

        self.update()
