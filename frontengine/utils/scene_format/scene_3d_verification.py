"""Real OpenGL acceptance. Run with python -m tests.integration.scene3d_gl_smoke.

No pytest/conftest and no software fallback. Uses a small, noninteractive window.
"""
import math
import tempfile
import time

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from OpenGL import GL

from frontengine.utils.scene_format.scene_3d_document import make_3d_scene
from frontengine.show.scene.runtime3d import Scene3DRuntime, prepare_models
from frontengine.show.scene.view3d import OffscreenScene3D, Scene3DView
from frontengine.utils.scene_format.scene_3d_fixtures import model_fixture


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def verify_native_scene():
    app = QApplication.instance() or QApplication([])
    require(app.platformName() not in ('offscreen', 'minimal'), 'Real desktop OpenGL is required')
    with tempfile.TemporaryDirectory(prefix='frontengine-3d-smoke-') as directory:
        path = model_fixture(directory)
        scene = make_3d_scene({'model': {'type': 'MODEL', 'file_path': str(path), 'clip': {'loop': False}}})
        scene.entries[scene.camera]['transform']['position'] = [0, 0, 5]
        scene.playback['duration'] = 2
        runtime = Scene3DRuntime(scene, prepare_models(scene))
        surface, view = None, None
        try:
            surface = OffscreenScene3D(runtime, (320, 180))
            surface.context.makeCurrent(surface.surface)
            version = GL.glGetString(GL.GL_VERSION).decode()
            renderer = GL.glGetString(GL.GL_RENDERER).decode()
            surface.context.doneCurrent()
            first = surface.frame()
            require(first.pixelColor(0, 0).alpha() == 0, 'Transparent background is not transparent')
            require(first.pixelColor(160, 90).alpha() > 0, 'Model center is empty')
            runtime.opacity = .5
            runtime._sample_stamp = None
            translucent = surface.frame().pixelColor(160, 90)
            require(126 <= translucent.alpha() <= 129, 'Object opacity was not preserved')
            require(abs(translucent.red()-first.pixelColor(160, 90).red()) <= 3, 'Premultiplied alpha was applied twice')
            runtime.opacity = 1
            runtime.timeline.seek(1)
            second = surface.frame()
            require(first != second, 'Bone and morph animation did not change the frame')
            # Validate the actual QWidget presentation as well as FBO output.
            view = Scene3DView(runtime)
            view.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
            view.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
            view.resize(320, 180)
            view.show()
            for _ in range(15):
                app.processEvents()
            require(view.viewport.isValid(), 'Desktop viewport has no valid OpenGL context')
            frame = view.output_frame()
            require(not frame.isNull(), 'Desktop viewport returned an empty frame')
            require(not view.viewport.error, view.viewport.error)
            from frontengine.ui.page.scene_setting.scene_actions import prepare_playback, close_playback
            candidate = prepare_playback(scene, app.screens(), models=prepare_models(scene))
            try:
                require(len(candidate.view_list) == len(app.screens()), 'Not all monitor candidates were initialized')
                require(candidate.view_list[0].viewport.isValid(), 'Playback transaction did not prime the target viewport')
                require(not candidate.view_list[0].isVisible(), 'Candidate playback became visible before adoption')
                from PySide6.QtGui import QImage, QColor
                previous = QImage(32, 18, QImage.Format.Format_RGBA8888_Premultiplied)
                previous.fill(QColor('blue'))
                target_view = candidate.view_list[0]
                target_view.begin_transition(previous)
                candidate.runtime3d.timeline.pause()
                candidate.runtime3d.timeline.seek(.25)
                blended = target_view.output_frame()
                corner = blended.pixelColor(0, 0)
                require(126 <= corner.alpha() <= 129 and corner.blue() > 250, 'Premultiplied scene transition is incorrect')
                _verify_screen_recreation(candidate, app)
            finally:
                close_playback(candidate)
            from frontengine.utils.scene_format.scene_3d_templates import BUILTIN_3D_TEMPLATES
            for template in BUILTIN_3D_TEMPLATES:
                template_runtime = Scene3DRuntime(template.entries(lambda key: key), preview=True)
                template_surface = template_view = None
                try:
                    template_surface = OffscreenScene3D(template_runtime, (320, 180))
                    pixels = bytes(template_surface.frame().constBits())
                    require(any(pixels[3::4]), '3D template rendered no visible content: '+template.identifier)
                    if not template_runtime.timeline.duration:
                        template_view = Scene3DView(template_runtime)
                        template_view.prime()
                        now = [0.]
                        template_runtime.timeline.clock = lambda: now[0]
                        template_runtime.set_owner('transition-acceptance', True)
                        template_view.begin_transition(previous)
                        now[0] = 1.
                        template_runtime.timeline.tick()
                        require(template_runtime.timeline.state == 'playing', 'Crossfade finished an open-ended scene')
                        require(not template_view.output_frame().isNull(), 'Open-ended scene stopped rendering after crossfade')
                finally:
                    if template_view:
                        template_view.close()
                    if template_surface:
                        template_surface.close()
                    template_runtime.close()
            from frontengine.ui.page.scene_setting.scene_setting_ui import SceneSettingUI
            page = SceneSettingUI()
            page.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
            page.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
            page.resize(1280, 800)
            try:
                page.visual_editor.document.reset(scene)
                page.show()
                page.tab_widget.setCurrentWidget(page.visual_editor)
                deadline = time.monotonic()+15
                while page.visual_editor.editor3d.runtime is None and time.monotonic() < deadline:
                    app.processEvents()
                    time.sleep(.005)
                editor = page.visual_editor.editor3d
                require(editor.runtime is not None, 'Editor model preparation did not complete')
                page.visual_editor._select_layer('model')
                editor.focus()
                _verify_transform_tools(editor, app)
                from PySide6.QtGui import QMouseEvent
                from PySide6.QtCore import QEvent, QPointF
                import numpy as np
                before_orbit = editor.viewport.camera[1][:3, 3].copy()
                viewport = editor.viewport
                viewport.mousePressEvent(QMouseEvent(QEvent.Type.MouseButtonPress, QPointF(100, 100), QPointF(100, 100),
                    Qt.MouseButton.RightButton, Qt.MouseButton.RightButton, Qt.KeyboardModifier.NoModifier))
                viewport.mouseMoveEvent(QMouseEvent(QEvent.Type.MouseMove, QPointF(140, 120), QPointF(140, 120),
                    Qt.MouseButton.NoButton, Qt.MouseButton.RightButton, Qt.KeyboardModifier.NoModifier))
                viewport.mouseReleaseEvent(QMouseEvent(QEvent.Type.MouseButtonRelease, QPointF(140, 120), QPointF(140, 120),
                    Qt.MouseButton.RightButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier))
                require(not np.allclose(before_orbit, viewport.camera[1][:3, 3]), 'Orbit did not move the camera around its target')
                require(abs(np.linalg.norm(before_orbit-viewport.orbit_target)-np.linalg.norm(viewport.camera[1][:3, 3]-viewport.orbit_target)) < 1e-6,
                        'Orbit changed the distance to its target')
                editor.apply_view()
                app.processEvents()
                require(not editor.viewport.error, editor.viewport.error)
                require(not editor.viewport.output_frame().isNull(), '3D editor failed to render its gizmo')
                page.open_output()
                page.output_dialog.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
                page.output_dialog.start_preview()
                deadline = time.monotonic()+15
                while page.output_dialog.preparing and time.monotonic() < deadline:
                    app.processEvents()
                    time.sleep(.005)
                require(page.output_dialog.session is not None, page.output_dialog.status.text())
                require(not page.output_dialog.session.frame().isNull(), 'Output dialog did not render the 3D scene')
                output = page.output_dialog.session
                original_size = output.frame().size()
                output.runtime3d.set_quality_tier('saver')
                output.runtime3d.set_low_power(True)
                require(output.frame().size() == original_size, 'Quality settings changed the fixed output size')
                require(output.runtime3d.timeline.timer.interval() == 250, 'Low-power clock was not applied to output')
            finally:
                page.close()
                app.processEvents()
            return {'platform': app.platformName(), 'gl_version': version, 'renderer': renderer,
                              'offscreen': [first.width(), first.height()], 'desktop': [frame.width(), frame.height()],
                              'transparent': True, 'animated': True, 'transaction_primed': True,
                              'editor': True, 'transition': True, 'output_dialog': True,
                              'direct_transform_tools': True, 'quality_fixed_output': True,
                              'templates': True, 'monitors': len(app.screens()),
                              'screen_recreation': 'native_views_simulated_disconnect',
                              'open_ended_transition': True}
        finally:
            if view:
                view.close()
                app.processEvents()
            if surface:
                surface.close()
            runtime.close()


def _verify_screen_recreation(candidate, app):
    topology = candidate.runtime3d.topology
    topology.start(candidate.view_list)
    runtime = candidate.runtime3d
    sources = dict(runtime.sources)
    for view in candidate.view_list:
        view.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
        view.show()
    app.processEvents()
    runtime.timeline.pause()
    runtime.timeline.seek(.75)
    original = list(candidate.view_list)
    for screen in app.screens():
        topology.screen_removed(screen)
    require(not candidate.view_list and not runtime.owners, 'Disconnected targets retained a render owner')
    for screen in app.screens():
        topology.screen_added(screen)
    app.processEvents()
    require(len(candidate.view_list) == len(original), 'Target reconnection did not restore every view')
    require(runtime.sources == sources, 'Target reconnection replaced shared media sources')
    require(math.isclose(runtime.timeline.position, .75) and not runtime.timeline.requested, 'Reconnection lost paused timeline position')
    for view in candidate.view_list:
        require(view not in original and view.viewport.isValid(), 'Reconnection did not recreate a valid native viewport')
        require(not view.output_frame().isNull(), 'Reconnected viewport returned no frame')


def _verify_transform_tools(editor, app):
    from copy import deepcopy
    from PySide6.QtCore import QEvent, QPointF
    from PySide6.QtGui import QMouseEvent
    viewport = editor.viewport
    document = editor.document
    def drag():
        viewport.gizmo_axes = []
        start = QPointF(viewport.width()/2+12, viewport.height()/2+12)
        end = start+QPointF(24, 0)
        for kind, point, button, buttons in (
            (QEvent.Type.MouseButtonPress, start, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton),
            (QEvent.Type.MouseMove, end, Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton),
            (QEvent.Type.MouseButtonRelease, end, Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton)):
            event = QMouseEvent(kind, point, point, button, buttons, Qt.KeyboardModifier.NoModifier)
            {QEvent.Type.MouseButtonPress: viewport.mousePressEvent, QEvent.Type.MouseMove: viewport.mouseMoveEvent,
             QEvent.Type.MouseButtonRelease: viewport.mouseReleaseEvent}[kind](event)
        app.processEvents()
    for tool, channel in (('move', 'position'), ('rotate', 'rotation'), ('scale', 'scale')):
        editor.tool.setCurrentIndex(editor.tool.findData(tool))
        editor.axis.setCurrentIndex(editor.axis.findData('x'))
        editor.snap.setChecked(True)
        before = deepcopy(document.entries['model']['transform'])
        count = document.undo.index()
        drag()
        after = document.entries['model']['transform']
        require(after[channel] != before[channel], 'Direct '+tool+' did not edit the selected model')
        require(document.undo.index() == count+1, 'A drag did not produce exactly one undo command')
        document.undo.undo()
        require(document.entries['model']['transform'] == before, 'Undo did not restore a 3D transform')
    document.update('model', {'locked': True})
    before = deepcopy(document.entries['model'])
    drag()
    require(document.entries['model'] == before, 'A locked model was transformed')
    document.update('model', {'locked': False})
    editor.snap.setChecked(False)
