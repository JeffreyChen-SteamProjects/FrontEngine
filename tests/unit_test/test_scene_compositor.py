from PySide6.QtGui import QColor, QImage

from frontengine.show.scene.scene import SceneManager


def test_scene_composition_preserves_layer_position_and_order():
    from frontengine.show.scene.compositor_view import SceneCompositorView
    manager = SceneManager()
    # Real widgets expose painter-produced images; no fake GL or scene parser.
    from frontengine.show.base_widget import BaseWidget
    class Square(BaseWidget):
        def __init__(self, color):
            super().__init__()
            self.color = color
            self.resize(16, 16)
            self.opacity = 1.0
        def draw_content(self, painter):
            painter.fillRect(self.rect(), QColor(self.color))
    for color, position, z in [('red', (0, 0), 0), ('blue', (8, 0), 1)]:
        widget = Square(color)
        widget.set_render_backend('software')
        proxy = manager.graphic_scene.addWidget(widget)
        proxy.setPos(*position)
        proxy.setZValue(z)
        manager.widget_list.append(proxy)
    view = SceneCompositorView(manager.graphic_scene, backend='software')
    view.resize(32, 32)
    frame = view.output_frame()
    assert frame.pixelColor(1, 1) == QColor('red')
    assert frame.pixelColor(9, 1) == QColor('blue')
    view.close()
    manager.clear()


def test_scene_proxy_forces_software_child_composition(tmp_path):
    image = QImage(16, 16, QImage.Format.Format_RGBA8888)
    image.fill(QColor('red'))
    path = tmp_path / 'image.png'
    image.save(str(path))
    manager = SceneManager()
    proxy = manager.add_image({'file_path': str(path), 'x': 24, 'y': 12, 'z': 2})
    assert proxy.sceneBoundingRect().topLeft().x() == 24
    assert proxy.zValue() == 2
    assert proxy.widget().render_backend == 'software'
    manager.clear()


def test_scene_compositor_respects_quality_refresh_tier():
    from frontengine.show.scene.compositor_view import SceneCompositorView
    manager = SceneManager()
    view = SceneCompositorView(manager.graphic_scene, backend='software')
    view.set_quality_tier('saver')
    assert view.timer.interval() >= 100
    view.set_quality_tier('high')
    assert view.timer.interval() == 33
    view.close()
    manager.clear()


def test_equal_z_scene_layers_preserve_qt_insertion_order():
    from frontengine.show.base_widget import BaseWidget
    from frontengine.show.scene.compositor_view import SceneCompositorView

    class Square(BaseWidget):
        def __init__(self, color):
            super().__init__()
            self.color = QColor(color)
            self.opacity = 1.0
            self.resize(16, 16)

        def draw_content(self, painter):
            painter.fillRect(self.rect(), self.color)

    manager = SceneManager()
    for color in ('red', 'blue'):
        widget = Square(color)
        widget.set_render_backend('software')
        manager.widget_list.append(manager.graphic_scene.addWidget(widget))
    view = SceneCompositorView(manager.graphic_scene, backend='software')
    view.resize(16, 16)
    try:
        assert view.output_frame().pixelColor(8, 8) == QColor('blue')
    finally:
        view.close()
        manager.clear()


def test_scene_clear_tolerates_manually_closed_native_windows():
    from PySide6.QtCore import QCoreApplication, QEvent, Qt
    from PySide6.QtWidgets import QWidget
    from shiboken6 import isValid
    manager = SceneManager()
    closed = QWidget()
    closed.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
    live = QWidget()
    live.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
    manager.native_widgets.extend([closed, live])
    manager.puppet_settings.append({'type': 'PUPPET'})
    closed.close()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    assert not isValid(closed)
    manager.clear()
    manager.clear()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    assert not isValid(live)
    assert manager.native_widgets == []
    assert manager.puppet_settings == []
    assert manager.graphic_scene.items() == []


def test_close_scene_tolerates_manually_closed_views_then_clears_remaining_content():
    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtWidgets import QWidget
    from shiboken6 import isValid
    from frontengine.show.scene.compositor_view import SceneCompositorView
    from frontengine.ui.page.scene_setting.scene_setting_ui import SceneSettingUI
    page = SceneSettingUI()
    closed = SceneCompositorView(page.scene.graphic_scene, backend='software')
    live = SceneCompositorView(page.scene.graphic_scene, backend='software')
    page.scene.view_list.extend([closed, live])
    proxy = page.scene.graphic_scene.addWidget(QWidget())
    page.scene.widget_list.append(proxy)
    closed.close()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    assert not isValid(closed)
    try:
        page.close_scene()
        page.close_scene()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        assert not isValid(live)
        assert page.scene.view_list == []
        assert page.scene.widget_list == []
        assert page.scene.graphic_scene.items() == []
    finally:
        page.close()
