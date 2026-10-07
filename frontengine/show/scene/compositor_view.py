"""Compose painter scene primitives as individual GPU textures, with fallback."""
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QTransform
from PySide6.QtWidgets import QWidget

from frontengine.show.compositor import CompositorWidget, Layer
from frontengine.show.window_helpers import apply_overlay_window_flags
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
        self.compositor.set_layers(layers)

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
        self.compositor.shutdown()
        super().closeEvent(event)

    def _set_media_active(self, active: bool) -> None:
        owners = getattr(self.scene, '_media_view_owners', set())
        owners.add(id(self)) if active else owners.discard(id(self))
        self.scene._media_view_owners = owners
        for proxy in self.scene.items():
            widget = proxy.widget() if hasattr(proxy, 'widget') else None
            if widget is not None and hasattr(widget, 'set_active'):
                widget.set_active(bool(owners) and proxy.isVisible())

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
