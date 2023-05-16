from PySide6.QtCore import QRect
from PySide6.QtGui import QPixmap, QImage, QFontDatabase

from frontengine.show.gif.paint_gif import GifWidget
from frontengine.show.scene.extend_graphic_scene import ExtendGraphicScene
from frontengine.show.scene.extend_graphic_view import ExtendGraphicView
from frontengine.show.sound_player.sound_player import SoundPlayer
from frontengine.show.video.video_player import VideoWidget
from frontengine.show.web.webview import WebWidget


class SceneManager(object):

    def __init__(
            self
    ):
        super().__init__()
        self.graphic_scene = ExtendGraphicScene()
        self.graphic_view = ExtendGraphicView(self.graphic_scene)
        self.graphic_view.showMaximized()

    def add_image(self, image_path: str, image_setting: dict = None):
        pixmap = self.graphic_scene.addPixmap(QPixmap().fromImage(QImage(image_path)))
        return pixmap

    def add_gif(self, gif_image_path: str, gif_setting: dict = None):
        gif_widget = GifWidget(gif_image_path)
        return self.graphic_scene.addWidget(gif_widget)

    def add_sound(self, sound_path: str, sound_setting: dict = None):
        sound_widget = SoundPlayer(sound_path)
        return self.graphic_scene.addWidget(sound_widget)

    def add_text(self, text: str, text_setting: dict = None):
        return self.graphic_scene.addText(text)

    def add_video(self, video_path: str, video_setting: dict = None):
        video_widget = VideoWidget(video_path)
        return self.graphic_scene.addWidget(video_widget)

    def add_web(self, url: str, web_setting: dict = None):
        web_widget = WebWidget(url)
        return self.graphic_scene.addWidget(web_widget)
