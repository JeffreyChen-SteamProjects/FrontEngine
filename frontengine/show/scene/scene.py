from PySide6.QtWidgets import QWidget, QGraphicsView

from frontengine.show.scene.extend_graphic_scene import ExtendGraphicScene
from frontengine.show.scene.extend_graphic_view import ExtendGraphicView


class SceneWidget(QWidget):

    def __init__(
            self,
            # gif_detail: dict,
            # image_detail: dict,
            # sound_player_detail: dict,
            # text_detail: dict,
            # video_detail: dict,
            # web_detail: dict
    ):
        super().__init__()
        # Layout
        # self.setWindowFlag(
        #     Qt.WindowType.WindowTransparentForInput |
        #     Qt.WindowType.FramelessWindowHint |
        #     Qt.WindowType.WindowStaysOnTopHint |
        #     Qt.WindowType.Tool
        # )
        self.graphic_scene = ExtendGraphicScene()
        self.graphic_view = ExtendGraphicView(self.graphic_scene)
        self.graphic_view.showMaximized()
