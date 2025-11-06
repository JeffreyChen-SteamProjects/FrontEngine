from typing import List, Dict, Any, Optional

from PySide6.QtWidgets import QGraphicsProxyWidget

from frontengine.show.gif.paint_gif import GifWidget
from frontengine.show.image.paint_image import ImageWidget
from frontengine.show.scene.extend_graphic_scene import ExtendGraphicScene
from frontengine.show.scene.extend_graphic_view import ExtendGraphicView
from frontengine.show.sound_player.sound_player import SoundPlayer
from frontengine.show.text.draw_text import TextWidget
from frontengine.show.video.video_player import VideoWidget
from frontengine.show.web.webview import WebWidget
from frontengine.utils.logging.loggin_instance import front_engine_logger


class SceneManager:
    """
    SceneManager: 管理場景與多媒體元件的統一入口
    SceneManager: Unified manager for scene and multimedia widgets
    """

    def __init__(self) -> None:
        front_engine_logger.info("[SceneManager] Init")
        super().__init__()
        self.graphic_scene: ExtendGraphicScene = ExtendGraphicScene()
        self.widget_list: List[QGraphicsProxyWidget] = []
        self.view_list: List[ExtendGraphicView] = []

    def _normalize_opacity(self, value: Optional[Any], default: float = 0.2) -> float:
        """
        將設定值轉換為透明度 (0~1)
        Normalize opacity value (0~1)
        """
        try:
            return float(value) / 100 if value is not None else default
        except (ValueError, TypeError):
            return default

    def _normalize_int(self, value: Optional[Any], default: int) -> int:
        """
        將設定值轉換為整數
        Normalize integer value
        """
        try:
            return int(value) if value is not None else default
        except (ValueError, TypeError):
            return default

    def _normalize_float(self, value: Optional[Any], default: float) -> float:
        """
        將設定值轉換為浮點數
        Normalize float value
        """
        try:
            return float(value) if value is not None else default
        except (ValueError, TypeError):
            return default

    def add_image(self, setting_dict: Dict) -> QGraphicsProxyWidget:
        front_engine_logger.info(f"[SceneManager] add_image | settings={setting_dict}")
        image_widget = ImageWidget(setting_dict.get("file_path"))
        opacity = self._normalize_opacity(setting_dict.get("opacity"))
        image_widget.set_ui_variable(opacity)
        proxy_widget = self.graphic_scene.addWidget(image_widget)
        self.widget_list.append(proxy_widget)
        return proxy_widget

    def add_gif(self, setting_dict: Dict) -> QGraphicsProxyWidget:
        front_engine_logger.info(f"[SceneManager] add_gif | settings={setting_dict}")
        gif_widget = GifWidget(setting_dict.get("file_path"))
        speed = self._normalize_int(setting_dict.get("speed"), 100)
        opacity = self._normalize_opacity(setting_dict.get("opacity"))
        gif_widget.set_gif_variable(speed)
        gif_widget.set_ui_variable(opacity)
        proxy_widget = self.graphic_scene.addWidget(gif_widget)
        self.widget_list.append(proxy_widget)
        return proxy_widget

    def add_sound(self, setting_dict: Dict) -> QGraphicsProxyWidget:
        front_engine_logger.info(f"[SceneManager] add_sound | settings={setting_dict}")
        sound_widget = SoundPlayer(setting_dict.get("file_path"))
        volume = self._normalize_float(setting_dict.get("volume"), 1.0) / 100
        sound_widget.set_player_variable(volume)
        proxy_widget = self.graphic_scene.addWidget(sound_widget)
        self.widget_list.append(proxy_widget)
        return proxy_widget

    def add_text(self, setting_dict: Dict) -> QGraphicsProxyWidget:
        front_engine_logger.info(f"[SceneManager] add_text | settings={setting_dict}")
        text_widget = TextWidget(setting_dict.get("text"))
        font_size = self._normalize_int(setting_dict.get("font_size"), 100)
        opacity = self._normalize_opacity(setting_dict.get("opacity"))
        alignment = setting_dict.get("alignment", "Center")
        text_widget.set_ui_variable(opacity)
        text_widget.set_font_variable(font_size)
        text_widget.set_alignment(alignment)
        proxy_widget = self.graphic_scene.addWidget(text_widget)
        self.widget_list.append(proxy_widget)
        return proxy_widget

    def add_video(self, setting_dict: Dict) -> QGraphicsProxyWidget:
        front_engine_logger.info(f"[SceneManager] add_video | settings={setting_dict}")
        video_widget = VideoWidget(setting_dict.get("file_path"))
        opacity = self._normalize_opacity(setting_dict.get("opacity"))
        volume = self._normalize_float(setting_dict.get("volume"), 1.0) / 100
        play_rate = self._normalize_float(setting_dict.get("play_rate"), 1.0) / 100
        video_widget.set_ui_variable(opacity)
        video_widget.set_player_variable(play_rate, volume)
        proxy_widget = self.graphic_scene.addWidget(video_widget)
        self.widget_list.append(proxy_widget)
        return proxy_widget

    def add_web(self, setting_dict: Dict) -> QGraphicsProxyWidget:
        front_engine_logger.info(f"[SceneManager] add_web | settings={setting_dict}")
        web_widget = WebWidget(setting_dict.get("url"))
        opacity = self._normalize_opacity(setting_dict.get("opacity"))
        web_widget.set_ui_variable(opacity)
        proxy_widget = self.graphic_scene.addWidget(web_widget)
        self.widget_list.append(proxy_widget)
        return proxy_widget