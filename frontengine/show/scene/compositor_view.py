"""Compose painter scene primitives as individual GPU textures, with fallback."""
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QTransform, QImage
from PySide6.QtWidgets import QWidget
import numpy

from frontengine.show.compositor import CompositorWidget, Layer
from frontengine.show.compositor.layers import compose_frame
from frontengine.show.window_helpers import apply_overlay_window_flags
from frontengine.show.scene.timeline import SceneTimeline
from frontengine.user_setting.user_setting_file import user_setting_dict
from frontengine.utils.power_mode.power_mode import normalize_tier, tier_interval, scaled_interval


class SceneCompositorView(QWidget):
    def __init__(self, scene, backend: str = 'auto') -> None:
        super().__init__()
        self.scene = scene
        self.opacity = 1.0
        self._zoom = 1.0
        self._pan = QTransform()
        self._drag_position = None
        self.previous_frame = QImage()
        self.transition_seconds = 0.0
        self.timeline = getattr(scene, '_scene_timeline', None)
        if self.timeline is None:
            self.timeline = SceneTimeline(scene, lambda values: apply_scene_animation(scene, values))
            scene._scene_timeline = self.timeline
            self.timeline.configure({item.data(0): item.data(1) for item in scene.items()
                                     if item.data(0) and isinstance(item.data(1), dict)})
            self.timeline.play()
        self.timeline.state_changed.connect(self._timeline_state)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        apply_overlay_window_flags(self, allow_input=True)
        self.compositor = CompositorWidget(self, backend)
        self.compositor.show()
        self.timer = QTimer(self)
        self.quality_tier = normalize_tier(user_setting_dict.get('quality_tier'))
        self.apply_quality_tier()
        self.timer.timeout.connect(self._refresh)

    def set_quality_tier(self, tier: str) -> None:
        """Apply the global quality tier to scene refresh and child rasterization."""
        self.quality_tier = normalize_tier(tier)
        for proxy in self.scene.items():
            widget = proxy.widget() if hasattr(proxy, 'widget') else None
            if widget is not None and hasattr(widget, 'set_quality_tier'):
                widget.set_quality_tier(self.quality_tier)
        self.apply_quality_tier()

    def apply_quality_tier(self) -> None:
        """Respect refresh limits and the current low-power preference."""
        interval = tier_interval(33, self.quality_tier)
        self.timer.setInterval(scaled_interval(interval, bool(user_setting_dict.get('low_power'))))

    def _refresh(self) -> None:
        transform = QTransform().scale(self._zoom, self._zoom) * self._pan
        layers = []
        # Keep Qt's stacking order for siblings that share the same z value.
        for index, proxy in enumerate(self.scene.items(Qt.SortOrder.AscendingOrder)):
            if not proxy.isVisible():
                continue
            widget = proxy.widget() if hasattr(proxy, 'widget') else None
            if widget is None or not hasattr(widget, 'output_frame'):
                continue
            layers.append(Layer(str(index), widget.output_frame(), proxy.sceneTransform() * transform,
                                proxy.zValue(), proxy.opacity() * self.opacity))
        self.compositor.setGeometry(self.rect())
        self.compositor.set_layers(self._transition_layers(layers))

    def _transition_layers(self, layers: list[Layer]) -> list[Layer]:
        if self.previous_frame.isNull():
            return layers
        blend = min(1, self.timeline.position / self.transition_seconds)
        if blend >= 1:
            self.previous_frame = QImage()
            return layers
        current = compose_frame(layers, self.size())
        return [Layer('transition', crossfade_images(current, self.previous_frame, blend))]

    def output_frame(self):
        self._refresh()
        return self.compositor.output_frame()

    @property
    def render_backend(self) -> str:
        return self.compositor.actual_backend

    @property
    def render_failure_reason(self) -> str:
        return self.compositor.failure_reason

    def set_render_backend(self, backend: str) -> None:
        self.compositor.shutdown()
        self.compositor.deleteLater()
        self.compositor = CompositorWidget(self, backend)
        self.compositor.show()
        self._refresh()

    def set_ui_variable(self, opacity: float) -> None:
        self.opacity = max(0.0, min(1.0, float(opacity)))
        self._refresh()

    def showEvent(self, event) -> None:
        self._set_media_active(True)
        self._refresh()
        self.timer.start()
        super().showEvent(event)

    def hideEvent(self, event) -> None:
        self._set_media_active(False)
        self.timer.stop()
        super().hideEvent(event)

    def resizeEvent(self, event) -> None:
        self.compositor.setGeometry(self.rect())
        super().resizeEvent(event)

    def wheelEvent(self, event) -> None:
        self._zoom = max(0.5, min(50.0, self._zoom * (1.1 if event.angleDelta().y() > 0 else 1 / 1.1)))
        self._refresh()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = event.position()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_position is not None:
            delta = event.position() - self._drag_position
            self._pan.translate(delta.x(), delta.y())
            self._drag_position = event.position()
            self._refresh()

    def mouseReleaseEvent(self, event) -> None:
        self._drag_position = None

    def closeEvent(self, event) -> None:
        self._set_media_active(False)
        self.timer.stop()
        self.previous_frame = QImage()
        self.compositor.shutdown()
        super().closeEvent(event)

    def _set_media_active(self, active: bool) -> None:
        owners = getattr(self.scene, '_media_view_owners', set())
        if active:
            owners.add(id(self))
        else:
            owners.discard(id(self))
        self.scene._media_view_owners = owners
        self.timeline.set_active(bool(owners))
        self._timeline_state(self.timeline.state)

    def _timeline_state(self, _state: str) -> None:
        owners = getattr(self.scene, '_media_view_owners', set())
        for proxy in self.scene.items():
            widget = proxy.widget() if hasattr(proxy, 'widget') else None
            if widget is not None and hasattr(widget, 'set_active'):
                widget.set_active(bool(owners) and proxy.isVisible() and self.timeline.state != 'paused')

    def begin_transition(self, previous: QImage, seconds: float = .5) -> None:
        """Crossfade a bounded outgoing snapshot; no old native resources survive."""
        if previous is None or previous.isNull():
            return
        self.previous_frame = previous.scaled(1920, 1080, Qt.AspectRatioMode.KeepAspectRatio)
        self.transition_seconds = max(.1, min(5, float(seconds)))
        self.timeline.minimum_duration = self.transition_seconds
        self.timeline.duration = max(self.timeline.duration, self.transition_seconds)
        self.timeline.play(restart=True)

    def mouseDoubleClickEvent(self, event) -> None:
        transform = QTransform().scale(self._zoom, self._zoom) * self._pan
        inverse, valid = transform.inverted()
        proxy = self.scene.itemAt(inverse.map(event.position()), QTransform()) if valid else None
        widget = proxy.widget() if proxy is not None and hasattr(proxy, 'widget') else None
        if widget is not None and hasattr(widget, 'interact'):
            widget.interact()
        super().mouseDoubleClickEvent(event)

    def set_muted(self, muted: bool) -> None:
        """Forward control-center mute to media retained by this scene."""
        for proxy in self.scene.items():
            widget = proxy.widget() if hasattr(proxy, 'widget') else None
            if widget is not None and hasattr(widget, 'set_muted'):
                widget.set_muted(muted)


def apply_scene_animation(scene, values: dict) -> None:
    """Apply sampled values without overwriting saved layer settings."""
    for proxy in scene.items():
        if proxy.data(0) not in values or not hasattr(proxy, 'widget'):
            continue
        value = values[proxy.data(0)]
        proxy.setPos(value['x'], value['y'])
        widget = proxy.widget()
        if widget is not None and hasattr(widget, 'set_ui_variable'):
            widget.set_ui_variable(value['opacity'] / 100)
            widget.update()


def crossfade_images(current: QImage, previous: QImage, ratio: float) -> QImage:
    """Mix premultiplied color and alpha equally with bounded row temporaries."""
    result = current.convertToFormat(QImage.Format.Format_RGBA8888_Premultiplied)
    old = previous.scaled(current.size()).convertToFormat(QImage.Format.Format_RGBA8888_Premultiplied)
    output = numpy.frombuffer(result.bits(), numpy.uint8).reshape((result.height(), result.bytesPerLine()))
    source = numpy.frombuffer(old.constBits(), numpy.uint8).reshape((old.height(), old.bytesPerLine()))
    weight = round(max(0, min(1, ratio)) * 255)
    for row in range(0, result.height(), 32):
        selected = slice(row, row + 32)
        output[selected] = ((output[selected].astype(numpy.uint16) * weight +
                             source[selected].astype(numpy.uint16) * (255 - weight) + 127) // 255).astype(numpy.uint8)
    return result
