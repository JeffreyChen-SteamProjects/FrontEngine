from typing import Dict, List

from PySide6.QtWidgets import QGraphicsProxyWidget

from frontengine.show.overlay_factory import build_overlay
from frontengine.show.scene.extend_graphic_scene import ExtendGraphicScene
from frontengine.show.scene.extend_graphic_view import ExtendGraphicView
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

    def _add(self, kind: str, setting_dict: Dict) -> QGraphicsProxyWidget:
        front_engine_logger.info(f"[SceneManager] add_{kind} | settings={setting_dict}")
        widget = build_overlay(kind, setting_dict)
        proxy_widget = self.graphic_scene.addWidget(widget)
        self.widget_list.append(proxy_widget)
        return proxy_widget

    def add_image(self, setting_dict: Dict) -> QGraphicsProxyWidget:
        return self._add("image", setting_dict)

    def add_gif(self, setting_dict: Dict) -> QGraphicsProxyWidget:
        return self._add("gif", setting_dict)

    def add_sound(self, setting_dict: Dict) -> QGraphicsProxyWidget:
        return self._add("sound", setting_dict)

    def add_text(self, setting_dict: Dict) -> QGraphicsProxyWidget:
        return self._add("text", setting_dict)

    def add_video(self, setting_dict: Dict) -> QGraphicsProxyWidget:
        return self._add("video", setting_dict)

    def add_web(self, setting_dict: Dict) -> QGraphicsProxyWidget:
        return self._add("web", setting_dict)
