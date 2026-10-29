"""Animated overlays hand new frames to the GPU compositor outside the paint pass."""
from PySide6.QtCore import QCoreApplication

from frontengine.show.base_widget import BaseWidget


class Animated(BaseWidget):
    def draw_content(self, painter) -> None:
        pass


class Compositor:
    def __init__(self) -> None:
        self.submissions = []

    def setGeometry(self, _rect) -> None:
        pass

    def set_layers(self, layers) -> None:
        self.submissions.append(layers)


def test_update_submits_new_content_without_waiting_for_paint():
    widget = Animated()
    try:
        widget._compositor = Compositor()
        widget.update()
        widget.update()
        widget.update()
        assert widget._compositor.submissions == []
        QCoreApplication.processEvents()
        # One coalesced submission per event-loop pass, built from the newest revision.
        assert len(widget._compositor.submissions) == 1
        assert widget._raster_signature[0] == widget._render_revision
        widget.update()
        QCoreApplication.processEvents()
        assert len(widget._compositor.submissions) == 2
    finally:
        widget._compositor = None
        widget.close()


def test_software_widgets_schedule_nothing_extra():
    widget = Animated()
    try:
        widget.update()
        assert not getattr(widget, '_compositor_pending', False)
    finally:
        widget.close()


def test_desktop_pets_always_paint_through_qt(tmp_path):
    """A pet moves its window every tick; the GPU compositor froze its frames while it moved."""
    from PySide6.QtGui import QColor, QImage

    from frontengine.show.pet.desktop_pet import DesktopPetWidget
    image = QImage(32, 32, QImage.Format.Format_ARGB32)
    image.fill(QColor('red'))
    image.save(str(tmp_path / 'pet.png'))
    pet = DesktopPetWidget(str(tmp_path / 'pet.png'), size=64, talk=False, sit_on_windows=False)
    try:
        pet.set_render_backend('gpu')
        pet.show()
        assert pet._compositor is None
        assert pet.render_backend == 'software'
    finally:
        pet.close()
