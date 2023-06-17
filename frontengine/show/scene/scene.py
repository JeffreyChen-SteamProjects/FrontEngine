from typing import List

from PySide6.QtWidgets import QGraphicsProxyWidget, QWidget
from frontengine.show.text.draw_text import TextWidget

from frontengine.show.gif.paint_gif import GifWidget
from frontengine.show.image.paint_image import ImageWidget
from frontengine.show.load.load_someone_make_ui import load_ui_file, read_extend_ui
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
        self.widget_list: List[QGraphicsProxyWidget] = list()

    def add_image(self, image_path: str, image_setting: dict = None) -> QGraphicsProxyWidget:
        image_widget = ImageWidget(image_path)
        opacity = image_setting.get("opacity")
        image_widget.set_ui_variable(opacity)
        proxy_widget = self.graphic_scene.addWidget(image_widget)
        self.widget_list.append(proxy_widget)
        return proxy_widget

    def add_gif(self, gif_image_path: str, gif_setting: dict = None) -> QGraphicsProxyWidget:
        gif_widget = GifWidget(gif_image_path)
        speed = gif_setting.get("speed")
        speed = speed if speed is not None else 100
        opacity = gif_setting.get("opacity")
        opacity = opacity if opacity is not None else 0.2
        gif_widget.set_gif_variable(speed)
        gif_widget.set_ui_variable(opacity)
        proxy_widget = self.graphic_scene.addWidget(gif_widget)
        self.widget_list.append(proxy_widget)
        return proxy_widget

    def add_sound(self, sound_path: str, sound_setting: dict = None) -> QGraphicsProxyWidget:
        sound_widget = SoundPlayer(sound_path)
        volume = sound_setting.get("volume")
        volume = volume if volume is not None else 1
        sound_widget.set_player_variable(volume)
        proxy_widget = self.graphic_scene.addWidget(sound_widget)
        self.widget_list.append(proxy_widget)
        return proxy_widget

    def add_text(self, text: str, text_setting: dict = None) -> QGraphicsProxyWidget:
        text_widget = TextWidget(text)
        font_size = text_setting.get("font_size")
        font_size = font_size if font_size is not None else 100
        opacity = text_setting.get("opacity")
        opacity = opacity if opacity is not None else 0.2
        text_widget.set_ui_variable(opacity)
        text_widget.set_font_variable(font_size)
        proxy_widget = self.graphic_scene.addWidget(text_widget)
        self.widget_list.append(proxy_widget)
        return proxy_widget

    def add_video(self, video_path: str, video_setting: dict = None) -> QGraphicsProxyWidget:
        video_widget = VideoWidget(video_path)
        opacity = video_setting.get("opacity")
        opacity = opacity if opacity is not None else 0.2
        volume = video_setting.get("volume")
        volume = volume if volume is not None else 1
        play_rate = video_setting.get("play_rate")
        play_rate = play_rate if play_rate is not None else 1
        video_widget.set_ui_variable(opacity)
        video_widget.set_player_variable(play_rate, volume)
        proxy_widget = self.graphic_scene.addWidget(video_widget)
        self.widget_list.append(proxy_widget)
        return proxy_widget

    def add_web(self, url: str, web_setting: dict = None) -> QGraphicsProxyWidget:
        web_widget = WebWidget(url)
        opacity = web_setting.get("opacity")
        opacity = opacity if opacity is not None else 0.2
        enable_input = web_setting.get("enable_input")
        enable_input = enable_input if enable_input is not None else False
        web_widget.set_ui_variable(opacity)
        web_widget.set_ui_window_flag(enable_input=enable_input)
        proxy_widget = self.graphic_scene.addWidget(web_widget)
        self.widget_list.append(proxy_widget)
        return proxy_widget

    def add_extend_ui_file(self, ui_path: str) -> QGraphicsProxyWidget:
        extend_widget = load_ui_file(ui_path)
        proxy_widget = self.graphic_scene.addWidget(extend_widget)
        self.widget_list.append(proxy_widget)
        return proxy_widget

    def add_extend_ui(self, ui: QWidget) -> QGraphicsProxyWidget:
        extend_widget = read_extend_ui(ui)
        proxy_widget = self.graphic_scene.addWidget(extend_widget)
        self.widget_list.append(proxy_widget)
        return proxy_widget
