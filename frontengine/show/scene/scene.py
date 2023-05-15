from frontengine.show.scene.extend_graphic_scene import ExtendGraphicScene
from frontengine.show.scene.extend_graphic_view import ExtendGraphicView


class SceneManager(object):

    def __init__(
            self
    ):
        super().__init__()
        self.graphic_scene = ExtendGraphicScene()
        self.graphic_view = ExtendGraphicView(self.graphic_scene)
        self.graphic_view.showMaximized()
