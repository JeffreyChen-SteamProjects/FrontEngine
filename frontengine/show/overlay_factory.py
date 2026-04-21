from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type

from PySide6.QtWidgets import QWidget

from frontengine.show.gif.paint_gif import GifWidget
from frontengine.show.image.paint_image import ImageWidget
from frontengine.show.sound_player.sound_player import SoundPlayer
from frontengine.show.text.draw_text import TextWidget
from frontengine.show.video.video_player import VideoWidget
from frontengine.show.web.webview import WebWidget


def _normalize_opacity(value: Optional[Any], default: float = 0.2) -> float:
    try:
        return float(value) / 100 if value is not None else default
    except (ValueError, TypeError):
        return default


def _normalize_int(value: Optional[Any], default: int) -> int:
    try:
        return int(value) if value is not None else default
    except (ValueError, TypeError):
        return default


def _normalize_float(value: Optional[Any], default: float) -> float:
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default


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
        widget = ImageWidget(setting_dict.get("file_path"))
        widget.set_ui_variable(_normalize_opacity(setting_dict.get("opacity")))
        return widget


class GifOverlayFactory(OverlayFactory):
    def create(self, setting_dict: Dict[str, Any]) -> QWidget:
        widget = GifWidget(setting_dict.get("file_path"))
        widget.set_gif_variable(_normalize_int(setting_dict.get("speed"), 100))
        widget.set_ui_variable(_normalize_opacity(setting_dict.get("opacity")))
        return widget


class SoundOverlayFactory(OverlayFactory):
    def create(self, setting_dict: Dict[str, Any]) -> QWidget:
        widget = SoundPlayer(setting_dict.get("file_path"))
        volume = _normalize_float(setting_dict.get("volume"), 1.0) / 100
        widget.set_player_variable(volume)
        return widget


class TextOverlayFactory(OverlayFactory):
    def create(self, setting_dict: Dict[str, Any]) -> QWidget:
        widget = TextWidget(setting_dict.get("text"))
        widget.set_ui_variable(_normalize_opacity(setting_dict.get("opacity")))
        widget.set_font_variable(_normalize_int(setting_dict.get("font_size"), 100))
        widget.set_alignment(setting_dict.get("alignment", "Center"))
        return widget


class VideoOverlayFactory(OverlayFactory):
    def create(self, setting_dict: Dict[str, Any]) -> QWidget:
        widget = VideoWidget(setting_dict.get("file_path"))
        opacity = _normalize_opacity(setting_dict.get("opacity"))
        volume = _normalize_float(setting_dict.get("volume"), 1.0) / 100
        play_rate = _normalize_float(setting_dict.get("play_rate"), 1.0) / 100
        widget.set_ui_variable(opacity)
        widget.set_player_variable(play_rate, volume)
        return widget


class WebOverlayFactory(OverlayFactory):
    def create(self, setting_dict: Dict[str, Any]) -> QWidget:
        widget = WebWidget(setting_dict.get("url"))
        widget.set_ui_variable(_normalize_opacity(setting_dict.get("opacity")))
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
