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
        self.native_widgets: list = []
        self.puppet_settings: list[dict] = []

    def _add(self, kind: str, setting_dict: Dict) -> QGraphicsProxyWidget:
        front_engine_logger.info(f"[SceneManager] add_{kind} | settings={setting_dict}")
        from frontengine.utils.scene_format.scene_editor_document import validate_geometry
        validate_geometry({"layer": setting_dict})
        widget = build_overlay(kind, setting_dict)
        widget.overlay_remembers_geometry = False
        if "width" in setting_dict or "height" in setting_dict:
            widget.resize(int(setting_dict.get("width", widget.width())),
                          int(setting_dict.get("height", widget.height())))
        if hasattr(widget, 'set_render_backend'):
            widget.set_render_backend('software')
        proxy_widget = self.graphic_scene.addWidget(widget)
        proxy_widget.setPos(float(setting_dict.get('x', 0)), float(setting_dict.get('y', 0)))
        proxy_widget.setZValue(float(setting_dict.get('z', 0)))
        proxy_widget.setScale(float(setting_dict.get("scale", 1)))
        proxy_widget.setRotation(float(setting_dict.get("rotation", 0)))
        proxy_widget.setVisible(setting_dict.get("visible", True))
        self.widget_list.append(proxy_widget)
        return proxy_widget

    def supports_composition(self) -> bool:
        return bool(self.widget_list) and all(
            hasattr(proxy.widget(), 'output_frame') for proxy in self.widget_list)

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

    def add_puppet(self, setting_dict: Dict) -> None:
        from frontengine.utils.imervue.puppet_asset import validate_puppet, finite_parameters
        validate_puppet(setting_dict.get('file_path', ''))
        finite_parameters(setting_dict.get('parameters', {}))
        self.puppet_settings.append(dict(setting_dict))

    def open_native_widgets(self, monitor=None) -> None:
        for setting in self.puppet_settings:
            widget = build_overlay('puppet', setting)
            origin = monitor.availableGeometry().topLeft() if monitor else None
            if monitor:
                widget.setScreen(monitor)
            x, y = setting.get('x', 0), setting.get('y', 0)
            widget.move(int(x) + (origin.x() if origin else 0),
                        int(y) + (origin.y() if origin else 0))
            self.native_widgets.append(widget)
            widget.show()

    def clear(self) -> None:
        """
        真的把場景清空。只清 widget_list 不夠：項目還掛在 QGraphicsScene 上，
        音效會在沒有視窗的情況下繼續播，重開場景還會把舊的疊上來。
        Actually empty the scene. Clearing widget_list alone is not enough --
        the items stay in the QGraphicsScene, so sound keeps playing with no
        window on screen and restarting the scene stacks the old items on top.
        """
        front_engine_logger.info("[SceneManager] clear")
        native_widgets = tuple(self.native_widgets)
        self.native_widgets.clear()
        for widget in native_widgets:
            try:
                widget.close()
            except RuntimeError:  # WA_DeleteOnClose may have already deleted it.
                continue
        self.puppet_settings.clear()
        for proxy_widget in self.widget_list:
            try:
                widget = proxy_widget.widget()
                if widget is not None:
                    widget.close()
            except RuntimeError:  # pragma: no cover - proxy already deleted
                continue
        self.graphic_scene.clear_scene()
        self.widget_list.clear()
