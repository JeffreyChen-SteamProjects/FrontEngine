from typing import List, Dict

from PySide6.QtWidgets import QGraphicsProxyWidget
from frontengine.show.scene.extend_graphic_view import ExtendGraphicView

from frontengine.show.gif.paint_gif import GifWidget
from frontengine.show.image.paint_image import ImageWidget
from frontengine.show.scene.extend_graphic_scene import ExtendGraphicScene
from frontengine.show.sound_player.sound_player import SoundPlayer
from frontengine.show.text.draw_text import TextWidget
from frontengine.show.video.video_player import VideoWidget
from frontengine.show.web.webview import WebWidget
from frontengine.utils.logging.loggin_instance import front_engine_logger


class SceneManager(object):

    def __init__(
            self
    ):
        front_engine_logger.info("Init SceneManager")
        super().__init__()
        self.graphic_scene = ExtendGraphicScene()
        self.widget_list: List[QGraphicsProxyWidget] = list()
        self.view_list: List[ExtendGraphicView] = []

    def add_image(self, setting_dict: Dict) -> QGraphicsProxyWidget:
        front_engine_logger.info(f"SceneManager setting_dict: {setting_dict}")
        image_path = setting_dict.get("file_path")
        image_widget = ImageWidget(image_path)
        opacity = float(setting_dict.get("opacity")) / 100
        opacity = opacity if opacity is not None else 0.2
        image_widget.set_ui_variable(opacity)
        proxy_widget = self.graphic_scene.addWidget(image_widget)
        self.widget_list.append(proxy_widget)
        return proxy_widget

    def add_gif(self, setting_dict: Dict) -> QGraphicsProxyWidget:
        gif_image_path = setting_dict.get("file_path")
        gif_widget = GifWidget(gif_image_path)
        speed = int(setting_dict.get("speed"))
        speed = speed if speed is not None else 100
        opacity = float(setting_dict.get("opacity")) / 100
        opacity = opacity if opacity is not None else 0.2
        gif_widget.set_gif_variable(speed)
        gif_widget.set_ui_variable(opacity)
        proxy_widget = self.graphic_scene.addWidget(gif_widget)
        self.widget_list.append(proxy_widget)
        return proxy_widget

    def add_sound(self, setting_dict: Dict) -> QGraphicsProxyWidget:
        sound_path = setting_dict.get("file_path")
        sound_widget = SoundPlayer(sound_path)
        volume = float(setting_dict.get("volume")) / 100
        volume = volume if volume is not None else 1
        sound_widget.set_player_variable(volume)
        proxy_widget = self.graphic_scene.addWidget(sound_widget)
        self.widget_list.append(proxy_widget)
        return proxy_widget

    def add_text(self, setting_dict: Dict) -> QGraphicsProxyWidget:
        text = setting_dict.get("text")
        text_widget = TextWidget(text)
        font_size = int(setting_dict.get("font_size"))
        font_size = font_size if font_size is not None else 100
        opacity = float(setting_dict.get("opacity")) / 100
        opacity = opacity if opacity is not None else 0.2
        alignment = setting_dict.get("alignment", "Center")
        text_widget.set_ui_variable(opacity)
        text_widget.set_font_variable(font_size)
        text_widget.set_alignment(alignment)
        proxy_widget = self.graphic_scene.addWidget(text_widget)
        self.widget_list.append(proxy_widget)
        return proxy_widget

    def add_video(self, video_setting: Dict) -> QGraphicsProxyWidget:
        video_path = video_setting.get("file_path")
        video_widget = VideoWidget(video_path)
        opacity = float(video_setting.get("opacity")) / 100
        opacity = opacity if opacity is not None else 0.2
        volume = float(video_setting.get("volume")) / 100
        volume = volume if volume is not None else 1
        play_rate = float(video_setting.get("play_rate")) / 100
        play_rate = play_rate if play_rate is not None else 1
        video_widget.set_ui_variable(opacity)
        video_widget.set_player_variable(play_rate, volume)
        proxy_widget = self.graphic_scene.addWidget(video_widget)
        self.widget_list.append(proxy_widget)
        return proxy_widget

    def add_web(self, setting_dict: Dict) -> QGraphicsProxyWidget:
        url = setting_dict.get("url")
        web_widget = WebWidget(url)
        opacity = float(setting_dict.get("opacity")) / 100
        opacity = opacity if opacity is not None else 0.2
        web_widget.set_ui_variable(opacity)
        proxy_widget = self.graphic_scene.addWidget(web_widget)
        self.widget_list.append(proxy_widget)
        return proxy_widget
