from PySide6.QtCore import QRectF, QSize
from PySide6.QtGui import QColor, QImage, QTransform


def solid(color):
    image = QImage(4, 4, QImage.Format.Format_RGBA8888_Premultiplied)
    image.fill(QColor(color))
    return image


def test_layers_compose_alpha_z_transform_clip_and_dpi():
    from frontengine.show.compositor import Layer, compose_frame
    upper = Layer('upper', solid('blue'), z=2, opacity=0.5,
                  transform=QTransform.fromTranslate(2, 0), clip=QRectF(3, 0, 1, 4))
    lower = Layer('lower', solid('red'), z=1)
    frame = compose_frame([upper, lower], QSize(8, 4), dpr=2)
    assert frame.size() == QSize(16, 8)
    assert frame.devicePixelRatio() == 2
    assert frame.pixelColor(4, 2) == QColor('red')
    mixed = frame.pixelColor(6, 2)
    assert abs(mixed.red() - 127) <= 1
    assert abs(mixed.blue() - 128) <= 1
    assert frame.pixelColor(10, 2).alpha() == 0


def test_base_widget_raster_adapter_outputs_existing_content():
    from frontengine.show.base_widget import BaseWidget

    class Overlay(BaseWidget):
        def draw_content(self, painter):
            painter.fillRect(self.rect(), QColor('red'))

    widget = Overlay()
    widget.resize(8, 4)
    widget.set_ui_variable(0.5)
    widget.set_render_backend('software')
    frame = widget.output_frame()
    assert frame.pixelColor(2, 2).red() == 255
    assert abs(frame.pixelColor(2, 2).alpha() - 128) <= 1
    assert widget.render_backend == 'software'
    widget.close()


def test_invalid_native_context_automatically_falls_back_to_visible_software():
    from frontengine.show.compositor import CompositorWidget
    from PySide6.QtCore import Signal
    from PySide6.QtWidgets import QWidget

    class InvalidGL(QWidget):
        failed = Signal(str)

        def cleanup(self):
            pass

        def isValid(self):
            return False

    widget = CompositorWidget(backend='software')
    widget._gl = InvalidGL(widget)
    widget._gl.failed.connect(widget._fallback)
    widget._gl.show()
    widget._probe_gpu()
    assert widget.actual_backend == 'software'
    assert widget.failure_reason == 'OpenGL context could not be created'
    assert widget._gl.isHidden()
    widget.close()


def test_static_overlay_frame_is_cached_until_content_update():
    from frontengine.show.base_widget import BaseWidget

    class Overlay(BaseWidget):
        def __init__(self):
            super().__init__()
            self.color = QColor('red')
            self.draws = 0

        def draw_content(self, painter):
            self.draws += 1
            painter.fillRect(self.rect(), self.color)

    widget = Overlay()
    widget.resize(8, 4)
    widget.opacity = 1.0
    first = widget.output_frame()
    second = widget.output_frame()
    assert first.cacheKey() == second.cacheKey()
    assert widget.draws == 1
    # The caller may mutate its frame without changing the renderer's cached image.
    second.fill(QColor('green'))
    assert widget.output_frame().pixelColor(0, 0) == QColor('red')
    widget.color = QColor('blue')
    widget.update()
    third = widget.output_frame()
    assert third.cacheKey() != first.cacheKey()
    assert third.pixelColor(0, 0) == QColor('blue')
    assert widget.draws == 2
    widget.opacity = 0.5
    assert abs(widget.output_frame().pixelColor(0, 0).alpha() - 128) <= 1
    widget.close()


def test_gif_frame_change_invalidates_cached_overlay_frame(tmp_path):
    import numpy as np
    from frontengine.show.gif.paint_gif import GifWidget
    from frontengine.utils.recording.gif_writer import encode_gif
    red = np.zeros((4, 4, 3), dtype=np.uint8)
    red[:, :, 0] = 255
    blue = np.zeros((4, 4, 3), dtype=np.uint8)
    blue[:, :, 2] = 255
    path = tmp_path / 'animated.gif'
    path.write_bytes(encode_gif([red, blue], delay_ms=100))
    widget = GifWidget(str(path))
    widget.opacity = 1.0
    widget.movie.stop()
    assert widget.movie.jumpToFrame(0)
    first = widget.output_frame()
    assert first.pixelColor(0, 0).red() > 240
    assert widget.movie.jumpToFrame(1)
    second = widget.output_frame()
    assert second.cacheKey() != first.cacheKey()
    assert second.pixelColor(0, 0).blue() > 240
    widget.close()
