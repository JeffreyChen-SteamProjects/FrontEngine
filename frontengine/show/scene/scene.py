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

    def clear(self) -> None:
        """
        真的把場景清空。只清 widget_list 不夠：項目還掛在 QGraphicsScene 上，
        音效會在沒有視窗的情況下繼續播，重開場景還會把舊的疊上來。
        Actually empty the scene. Clearing widget_list alone is not enough --
        the items stay in the QGraphicsScene, so sound keeps playing with no
        window on screen and restarting the scene stacks the old items on top.
        """
        front_engine_logger.info("[SceneManager] clear")
        for proxy_widget in self.widget_list:
            try:
                widget = proxy_widget.widget()
                if widget is not None:
                    widget.close()
            except RuntimeError:  # pragma: no cover - proxy already deleted
                continue
        self.graphic_scene.clear_scene()
        self.widget_list.clear()
