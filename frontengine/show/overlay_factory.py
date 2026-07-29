from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type

from PySide6.QtWidgets import QWidget

from frontengine.show.gif.paint_gif import GifWidget
from frontengine.show.image.paint_image import ImageWidget
from frontengine.show.sound_player.sound_player import SoundPlayer
from frontengine.show.text.draw_text import TextWidget
from frontengine.show.video.video_player import VideoWidget
from frontengine.show.web.webview import WebWidget


def _normalize_percent(value: Optional[Any], default: float) -> float:
    """
    場景 JSON 裡的百分比欄位（不透明度、音量、播放速率）轉成 0.0-1.0。
    沒填就用 default——default 已經是最終比例，不要再除以 100。
    Turn a percentage field from the scene JSON (opacity, volume, play rate)
    into a 0.0-1.0 ratio. A missing field falls back to `default`, which is
    already the final ratio and must not be divided again.
    """
    try:
        return float(value) / 100 if value is not None else default
    except (ValueError, TypeError):
        return default


def _normalize_int(value: Optional[Any], default: int) -> int:
    try:
        return int(value) if value is not None else default
    except (ValueError, TypeError):
        return default


def _require(setting_dict: Dict[str, Any], key: str, kind: str) -> str:
    """
    取出必要欄位。場景 JSON 是使用者自己編輯／外部提供的，缺欄位就明講，
    不要把 None 一路送進 Path() 或 QWebEngineView.load() 才炸在深處。
    Fetch a required field. Scene JSON is hand-edited or third-party, so say
    what is missing here instead of letting None reach Path() or
    QWebEngineView.load() and blow up somewhere deeper.
    """
    value = setting_dict.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Scene entry of type '{kind}' is missing a valid '{key}'")
    return value


class OverlayFactory(ABC):
    """
    Abstract factory for the overlay widget families (image, gif, video, ...).
    Each concrete factory owns the translation from a setting_dict (as read
    from the scene JSON) to a configured widget instance.
    """

    @abstractmethod
    def create(self, setting_dict: Dict[str, Any]) -> QWidget:
        ...


class ImageOverlayFactory(OverlayFactory):
    def create(self, setting_dict: Dict[str, Any]) -> QWidget:
        widget = ImageWidget(_require(setting_dict, "file_path", "image"))
        widget.set_ui_variable(_normalize_percent(setting_dict.get("opacity"), 0.2))
        return widget


class GifOverlayFactory(OverlayFactory):
    def create(self, setting_dict: Dict[str, Any]) -> QWidget:
        widget = GifWidget(_require(setting_dict, "file_path", "gif"))
        widget.set_gif_variable(_normalize_int(setting_dict.get("speed"), 100))
        widget.set_ui_variable(_normalize_percent(setting_dict.get("opacity"), 0.2))
        return widget


class SoundOverlayFactory(OverlayFactory):
    def create(self, setting_dict: Dict[str, Any]) -> QWidget:
        widget = SoundPlayer(_require(setting_dict, "file_path", "sound"))
        widget.set_player_variable(_normalize_percent(setting_dict.get("volume"), 1.0))
        return widget


class TextOverlayFactory(OverlayFactory):
    def create(self, setting_dict: Dict[str, Any]) -> QWidget:
        widget = TextWidget(_require(setting_dict, "text", "text"))
        widget.set_ui_variable(_normalize_percent(setting_dict.get("opacity"), 0.2))
        widget.set_font_variable(_normalize_int(setting_dict.get("font_size"), 100))
        widget.set_alignment(setting_dict.get("alignment", "Center"))
        return widget


class VideoOverlayFactory(OverlayFactory):
    def create(self, setting_dict: Dict[str, Any]) -> QWidget:
        widget = VideoWidget(_require(setting_dict, "file_path", "video"))
        widget.set_ui_variable(_normalize_percent(setting_dict.get("opacity"), 0.2))
        widget.set_player_variable(
            _normalize_percent(setting_dict.get("play_rate"), 1.0),
            _normalize_percent(setting_dict.get("volume"), 1.0),
        )
        return widget


class WebOverlayFactory(OverlayFactory):
    def create(self, setting_dict: Dict[str, Any]) -> QWidget:
        widget = WebWidget(_require(setting_dict, "url", "web"))
        widget.set_ui_variable(_normalize_percent(setting_dict.get("opacity"), 0.2))
        return widget


OVERLAY_FACTORY_REGISTRY: Dict[str, Type[OverlayFactory]] = {
    "image": ImageOverlayFactory,
    "gif": GifOverlayFactory,
    "sound": SoundOverlayFactory,
    "text": TextOverlayFactory,
    "video": VideoOverlayFactory,
    "web": WebOverlayFactory,
}


def build_overlay(kind: str, setting_dict: Dict[str, Any]) -> QWidget:
    """Convenience entry point: look the factory up by kind and build the widget."""
    factory_cls = OVERLAY_FACTORY_REGISTRY.get(kind)
    if factory_cls is None:
        raise ValueError(f"Unknown overlay kind: {kind}")
    return factory_cls().create(setting_dict)
