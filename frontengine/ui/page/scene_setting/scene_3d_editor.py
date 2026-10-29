"""3D viewport, transforms and scene controls integrated with the existing editor."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from threading import Event

import numpy as np
from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QDoubleSpinBox,
                              QCheckBox, QPushButton, QLabel, QFileDialog, QTreeWidget, QTreeWidgetItem,
                              QColorDialog, QSpinBox)

from frontengine.utils.multi_language.retranslate import tr, translate, retranslator
from frontengine.utils.scene_format.scene_3d_document import MEDIA_TYPES, DEFAULT_CAMERA
from frontengine.show.scene.math3d import euler_quaternion, quaternion_euler
from frontengine.show.scene.runtime3d import Scene3DRuntime, prepare_models
from frontengine.show.scene.view3d import Scene3DViewport
from frontengine.utils.scene_format.scene_resource_reads import SceneResourceRead


class _Signals(QObject):
    finished = Signal(int, object, object, str)


class _Prepare(QRunnable):
    def __init__(self, generation, scene, signals, cancel):
        super().__init__()
        self.generation, self.scene, self.signals = generation, scene, signals
        self.cancel = cancel
        self.read = SceneResourceRead(scene)

    def run(self):
        try:
            models = prepare_models(self.scene, self.cancel)
        except Exception as error:
            self.signals.finished.emit(self.generation, self.scene, None, str(error))
        else:
            self.signals.finished.emit(self.generation, self.scene, models, '')
        finally:
            self.read.close()


class Scene3DEditor(QWidget):
    selection_changed = Signal(object)

    def __init__(self, editor):
        super().__init__(editor)
        self.editor, self.document = editor, editor.document
        self.runtime, self.generation, self.closed = None, 0, False
        self.cancel = Event()
        self.resume_position, self.resume_playing = 0., False
        self.selected, self.fields, self.syncing = [], {}, False
        self.signals = _Signals()
        self.signals.finished.connect(self._prepared, Qt.ConnectionType.QueuedConnection)
        self.layout = QVBoxLayout(self)
        row = QHBoxLayout()
        self.tool, self.axis = QComboBox(), QComboBox()
        for value in ('move', 'rotate', 'scale'):
            self.tool.addItem(translate('scene3d_'+value, value), value)
        for value in ('free', 'x', 'y', 'z'):
            self.axis.addItem(translate('scene3d_'+value, value.upper()), value)
        self.local = tr(QCheckBox(), 'scene3d_local', 'Local axes')
        self.snap = tr(QCheckBox(), 'scene3d_snap', 'Snap')
        for widget in (self.tool, self.axis, self.local, self.snap):
            row.addWidget(widget)
        self.layout.addLayout(row)
        # Keep the normal 2D window raster-only until a 3D context has been verified.
        self.viewport = None
        self.placeholder = tr(QLabel(), 'scene3d_requires_gl', '3D preview requires desktop OpenGL 3.3')
        self.layout.addWidget(self.placeholder, 1)
        row = QHBoxLayout()
        for key, fallback, callback in (('scene3d_focus', 'Focus selection', self.focus),
                ('scene3d_reset_view', 'Reset view', self.reset_view), ('scene3d_apply_view', 'Use view as camera', self.apply_view),
                ('scene3d_retry', 'Retry', lambda: self.load(self.document.scene, force=True))):
            button = tr(QPushButton(), key, fallback)
            button.clicked.connect(callback)
            row.addWidget(button)
        self.layout.addLayout(row)
        self.status = tr(QLabel(), 'scene3d_controls', 'Right drag: orbit · Middle drag: pan · Wheel: dolly · Left drag: transform')
        self.status.setWordWrap(True)
        self.layout.addWidget(self.status)
        self.timer = QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self._refresh)
        self.tool.currentIndexChanged.connect(self._tools)
        self.axis.currentIndexChanged.connect(self._tools)
        self.local.toggled.connect(self._tools)
        self.snap.toggled.connect(self._tools)

    def _create_viewport(self):
        if self.viewport is not None:
            return
        self.viewport = Scene3DViewport(parent=self, editing=True)
        self.viewport.selection_changed.connect(self.selection_changed)
        self.viewport.axis_selected.connect(lambda axis: self.axis.setCurrentIndex(self.axis.findData(axis)))
        self.viewport.transform_committed.connect(self._commit_transform)
        self.viewport.failed.connect(self._error)
        self.layout.replaceWidget(self.placeholder, self.viewport)
        self.placeholder.hide()
        self.viewport.show()
        self._tools()

    def build_inspector(self, page):
        self.inspector = page
        section = page.add_section('scene3d_transform', '3D transform')
        self.space = QComboBox()
        self.space.addItem(translate('scene3d_world', 'World'), 'world')
        self.space.addItem(translate('scene3d_screen', 'Screen'), 'screen')
        self.space.currentIndexChanged.connect(self._apply)
        section.add_row('scene3d_space', self.space)
        self.parent_box = QComboBox()
        self.parent_box.currentIndexChanged.connect(self._apply)
        section.add_row('scene3d_parent', self.parent_box)
        color = tr(QPushButton(), 'scene3d_color', 'Color')
        color.clicked.connect(self._color)
        section.add_widget(color)
        for group, default in (('position', 0), ('rotation', 0), ('scale', 1)):
            row = QWidget()
            layout = QHBoxLayout(row)
            layout.setContentsMargins(0, 0, 0, 0)
            for axis in 'xyz':
                spin = QDoubleSpinBox()
                spin.setDecimals(3)
                spin.setRange(-100000, 100000)
                spin.setValue(default)
                spin.setPrefix(axis.upper()+': ')
                spin.editingFinished.connect(self._apply)
                self.fields[group+'_'+axis] = spin
                layout.addWidget(spin)
            section.add_row('scene3d_'+group, row)
        self.properties = {}
        for name, low, high, default in (('fov', .1, 179, 45), ('ortho_height', .001, 100000, 10.8),
                ('intensity', 0, 100000, 1), ('metallic', 0, 1, 0), ('roughness', .045, 1, .7)):
            spin = QDoubleSpinBox()
            spin.setRange(low, high)
            spin.setDecimals(3)
            spin.setValue(default)
            spin.editingFinished.connect(self._apply)
            self.properties[name] = spin
            section.add_row('scene3d_'+name, spin)
        self.projection = QComboBox()
        self.projection.addItem(translate('scene3d_perspective', 'Perspective'), 'perspective')
        self.projection.addItem(translate('scene3d_orthographic', 'Orthographic'), 'orthographic')
        self.projection.currentIndexChanged.connect(self._apply)
        section.add_row('scene3d_projection', self.projection)
        self.light_type = QComboBox()
        self.light_type.addItem(translate('scene3d_directional', 'Directional'), 'directional')
        self.light_type.addItem(translate('scene3d_point', 'Point'), 'point')
        self.light_type.currentIndexChanged.connect(self._apply)
        section.add_row('scene3d_light_type', self.light_type)
        self.clip = QComboBox()
        self.clip.currentIndexChanged.connect(self._apply)
        section.add_row('scene3d_clip', self.clip)
        self.clip_start, self.clip_rate = QDoubleSpinBox(), QDoubleSpinBox()
        self.clip_start.setRange(0, 3600)
        self.clip_rate.setRange(.1, 4)
        self.clip_rate.setValue(1)
        self.clip_loop = tr(QCheckBox(), 'scene3d_loop', 'Loop')
        for widget in (self.clip_start, self.clip_rate):
            widget.editingFinished.connect(self._apply)
        self.clip_loop.toggled.connect(self._apply)
        section.add_row('scene3d_clip_start', self.clip_start)
        section.add_row('scene3d_clip_rate', self.clip_rate)
        section.add_widget(self.clip_loop)
        self.playback_camera = QComboBox()
        self.playback_camera.currentIndexChanged.connect(self._camera_changed)
        section.add_row('scene3d_camera', self.playback_camera)
        self.node_tree = QTreeWidget()
        self.node_tree.setHeaderHidden(True)
        self.node_tree.setMaximumHeight(160)
        section.add_widget(self.node_tree)
        self._build_timeline(page)
        scene_section = page.add_section('scene3d_scene_settings', 'Scene settings')
        self.canvas_width, self.canvas_height = QSpinBox(), QSpinBox()
        for widget in (self.canvas_width, self.canvas_height):
            widget.setRange(16, 8192)
            widget.editingFinished.connect(self._scene_settings)
        scene_section.add_row('scene_property_width', self.canvas_width)
        scene_section.add_row('scene_property_height', self.canvas_height)
        self.background_button = tr(QPushButton(), 'scene3d_background', 'Background color / transparency')
        self.background_button.clicked.connect(self._background)
        scene_section.add_widget(self.background_button)

    def _build_timeline(self, page):
        section = page.add_section('scene_animation_title', 'Animation')
        self.position = QDoubleSpinBox()
        self.position.setRange(0, 3600)
        self.position.setDecimals(3)
        self.position.editingFinished.connect(self.seek)
        section.add_row('scene_animation_time', self.position)
        self.rate = QDoubleSpinBox()
        self.rate.setRange(.1, 4)
        self.rate.setSingleStep(.1)
        self.rate.setValue(1)
        self.rate.editingFinished.connect(self._playback_settings)
        section.add_row('scene3d_rate', self.rate)
        self.duration = QDoubleSpinBox()
        self.duration.setRange(0, 3600)
        self.duration.setSpecialValueText(translate('scene3d_auto', 'Automatic'))
        self.duration.editingFinished.connect(self._playback_settings)
        section.add_row('scene3d_duration', self.duration)
        self.loop = tr(QCheckBox(), 'scene3d_loop', 'Loop')
        self.loop.toggled.connect(self._playback_settings)
        section.add_widget(self.loop)
        self.click_through = tr(QCheckBox(), 'scene3d_clickthrough', 'Pass desktop clicks through')
        self.click_through.toggled.connect(self._playback_settings)
        section.add_widget(self.click_through)
        buttons = []
        for name, fallback, callback in (('scene_animation_play', 'Play', lambda: self.control('play')),
                ('scene_animation_pause', 'Pause', lambda: self.control('pause')),
                ('scene_animation_reset', 'Stop', lambda: self.control('reset')),
                ('scene_animation_replay', 'Replay', lambda: self.control('replay')),
                ('scene_animation_edit', 'Edit keyframes', self.editor._edit_animation)):
            button = tr(QPushButton(), name, fallback)
            button.clicked.connect(callback)
            buttons.append(button)
        section.add_actions(*buttons)

    def _tools(self):
        if self.tool.currentData() == 'scale':
            self.local.blockSignals(True)
            self.local.setChecked(True)
            self.local.blockSignals(False)
        self.local.setEnabled(self.tool.currentData() != 'scale')
        if self.viewport:
            self.viewport.tool, self.viewport.axis = self.tool.currentData(), self.axis.currentData()
            self.viewport.local, self.viewport.snap = self.local.isChecked(), self.snap.isChecked()

    def _commit_transform(self, entries):
        try:
            self.document.replace(entries, 'Transform 3D objects')
        except ValueError as error:
            self._error(error)

    def load(self, document, force=False):
        if self.closed:
            return
        self.generation += 1
        self.cancel.set()
        if document.mode != '3d':
            if self.runtime:
                self.runtime.close()
                self.runtime.deleteLater()
                self.runtime = None
            if self.viewport:
                self.viewport.set_runtime(None)
            return
        self.select(self.selected)
        if self.runtime and not force and self.runtime.update_document(document):
            self._playback_update()
            if self.viewport:
                self.viewport.update()
            return
        if self.runtime:
            self.resume_position, self.resume_playing = self.runtime.timeline.position, self.runtime.timeline.requested
            if self.viewport:
                self.viewport.set_runtime(None)
            self.runtime.close()
            self.runtime.deleteLater()
            self.runtime = None
        retranslator.set_text(self.status, 'scene_action_loading', 'Loading scene…')
        self.cancel = Event()
        QThreadPool.globalInstance().start(_Prepare(self.generation, document.copy(), self.signals, self.cancel))

    def _prepared(self, generation, document, models, error):
        if self.closed or generation != self.generation:
            return
        if error:
            self._error(error)
            return
        if QGuiApplication.platformName() in ('offscreen', 'minimal'):
            self._error(translate('scene3d_requires_gl', '3D preview requires desktop OpenGL 3.3'))
            return
        from frontengine.user_setting.user_setting_file import user_setting_dict
        if user_setting_dict.get('render_backend', 'auto') == 'software':
            self._error(translate('scene3d_requires_gl'))
            return
        candidate = None
        try:
            candidate = Scene3DRuntime(document, models, preview=True,
                                       enable_media=self.editor.media_enabled.isChecked())
            from frontengine.show.scene.view3d import OffscreenScene3D
            probe = OffscreenScene3D(candidate, (320, 180))
            try:
                probe.frame()
            finally:
                probe.close()
            self._create_viewport()
            candidate.failed.connect(self._error)
            position = self.runtime.timeline.position if self.runtime else self.resume_position
            playing = self.runtime.timeline.requested if self.runtime else self.resume_playing
            candidate.timeline.seek(position)
            candidate.timeline.changed.connect(self.editor._animation_position)
            if self.runtime:
                self.runtime.close()
                self.runtime.deleteLater()
            self.runtime = candidate
            candidate.performance_changed.connect(lambda interval, _scale: self.timer.setInterval(interval))
            self.timer.setInterval(candidate.timeline.timer.interval())
            self.viewport.set_runtime(candidate)
            candidate.set_owner(id(self), self.isVisible())
            if playing:
                candidate.timeline.play()
            self._playback_update()
            self.select(self.selected)
            retranslator.set_text(self.status, 'scene3d_controls', 'Right drag: orbit · Middle drag: pan · Wheel: dolly · Left drag: transform')
        except Exception as error:
            if candidate and candidate is not self.runtime:
                candidate.close()
            self._error(error)

    def _error(self, error):
        retranslator.forget(self.status)
        self.status.setText(str(error))

    def _refresh(self):
        if self.runtime:
            self.position.setValue(self.runtime.timeline.position)
        if self.viewport:
            self.viewport.update()

    def select(self, keys):
        self.selected = [key for key in keys if key in self.document.entries]
        if self.viewport:
            self.viewport.selected = self.selected
            self.viewport.update()
        self.syncing = True
        try:
            entry = self.document.entries[self.selected[0]] if len(self.selected) == 1 else None
            enabled = entry is not None and not entry.get('locked', False)
            self.inspector.setEnabled(self.document.scene.mode == '3d')
            for group, values in (('position', (entry or {}).get('transform', {}).get('position', [0, 0, 0])),
                    ('rotation', quaternion_euler((entry or {}).get('transform', {}).get('rotation', [0, 0, 0, 1]))),
                    ('scale', (entry or {}).get('transform', {}).get('scale', [1, 1, 1]))):
                for axis, value in zip('xyz', values):
                    spin = self.fields[group+'_'+axis]
                    spin.setEnabled(enabled)
                    spin.setValue(value)
            kind = (entry or {}).get('type')
            self.space.setEnabled(enabled and kind in MEDIA_TYPES)
            self.space.setCurrentIndex(self.space.findData((entry or {}).get('space', 'screen' if kind in MEDIA_TYPES else 'world')))
            self.parent_box.clear()
            self.parent_box.addItem(translate('scene3d_no_parent', 'No parent'), None)
            for key, value in self.document.entries.items():
                if key not in self.selected and value['type'] == 'GROUP':
                    self.parent_box.addItem(key, key)
            self.parent_box.setCurrentIndex(max(0, self.parent_box.findData((entry or {}).get('parent'))))
            self.parent_box.setEnabled(enabled)
            for name, spin in self.properties.items():
                spin.setEnabled(enabled and ((kind == 'CAMERA' and name in ('fov', 'ortho_height')) or
                    (kind == 'LIGHT' and name == 'intensity') or (kind in ('CUBE', 'SPHERE', 'PLANE') and name in ('metallic', 'roughness'))))
                spin.setValue((entry or {}).get(name, {'fov': 45, 'ortho_height': 10.8, 'intensity': 1, 'roughness': .7}.get(name, 0)))
            self.projection.setEnabled(enabled and kind == 'CAMERA')
            self.projection.setCurrentIndex(self.projection.findData((entry or {}).get('projection', 'perspective')))
            self.light_type.setEnabled(enabled and kind == 'LIGHT')
            self.light_type.setCurrentIndex(self.light_type.findData((entry or {}).get('light_type', 'directional')))
            self.playback_camera.clear()
            for key, value in self.document.entries.items():
                if value['type'] == 'CAMERA':
                    self.playback_camera.addItem(key, key)
            self.playback_camera.setCurrentIndex(self.playback_camera.findData(self.document.scene.camera))
            self.clip.clear()
            self.node_tree.clear()
            asset = self.runtime.models.get(str(Path(entry['file_path']).resolve())) if self.runtime and kind == 'MODEL' else None
            if asset:
                for i, clip in enumerate(asset.clips):
                    self.clip.addItem(clip['name'], i)
                def append(index, parent):
                    node = asset.nodes[index]
                    item = QTreeWidgetItem([node.get('name', f'Node {index}')])
                    parent.addChild(item) if isinstance(parent, QTreeWidgetItem) else parent.addTopLevelItem(item)
                    for child in node.get('children', []):
                        append(child, item)
                for index in asset.roots:
                    append(index, self.node_tree)
            clip = (entry or {}).get('clip', {})
            self.clip.setCurrentIndex(clip.get('index', 0))
            for widget in (self.clip, self.clip_start, self.clip_rate, self.clip_loop):
                widget.setEnabled(enabled and asset is not None and bool(asset.clips))
            self.clip_start.setValue(clip.get('start', 0))
            self.clip_rate.setValue(clip.get('rate', 1))
            self.clip_loop.setChecked(clip.get('loop', True))
        finally:
            self.syncing = False

    def _apply(self):
        if self.syncing or len(self.selected) != 1:
            return
        key = self.selected[0]
        entry = self.document.entries[key]
        if entry.get('locked'):
            return
        transform = {group: [self.fields[group+'_'+axis].value() for axis in 'xyz'] for group in ('position', 'rotation', 'scale')}
        transform['rotation'] = euler_quaternion(transform['rotation'])
        changes = {'transform': transform, 'parent': self.parent_box.currentData()}
        if changes['parent'] is None:
            changes['parent'] = None
        kind = entry['type']
        if kind in MEDIA_TYPES:
            changes['space'] = self.space.currentData()
        if kind == 'CAMERA':
            changes.update(projection=self.projection.currentData(), fov=self.properties['fov'].value(), ortho_height=self.properties['ortho_height'].value())
        if kind == 'LIGHT':
            changes.update(light_type=self.light_type.currentData(), intensity=self.properties['intensity'].value())
        if kind in ('CUBE', 'SPHERE', 'PLANE'):
            changes.update(metallic=self.properties['metallic'].value(), roughness=self.properties['roughness'].value())
        if kind == 'MODEL' and self.clip.count():
            changes['clip'] = {'index': self.clip.currentData(), 'start': self.clip_start.value(),
                               'rate': self.clip_rate.value(), 'loop': self.clip_loop.isChecked()}
        try:
            self.document.update(key, changes, 'Edit 3D object')
        except ValueError as error:
            self._error(error)

    def _camera_changed(self):
        if not self.syncing and self.playback_camera.currentData():
            scene = self.document.scene.copy()
            scene.camera = self.playback_camera.currentData()
            self.document.replace_document(scene, 'Choose playback camera')

    def _playback_update(self):
        self.syncing = True
        try:
            settings = self.document.scene.playback
            self.rate.setValue(settings.get('rate', 1))
            self.loop.setChecked(settings.get('loop', False))
            self.duration.setValue(settings.get('duration', 0))
            self.click_through.setChecked(settings.get('click_through', False))
            self.canvas_width.setValue(self.document.scene.canvas[0])
            self.canvas_height.setValue(self.document.scene.canvas[1])
            if self.runtime:
                self.runtime.timeline.set_rate(self.rate.value())
                self.runtime.timeline.set_loop(self.loop.isChecked())
        finally:
            self.syncing = False

    def _playback_settings(self):
        if self.syncing:
            return
        scene = self.document.scene.copy()
        scene.playback = {'rate': self.rate.value(), 'loop': self.loop.isChecked(),
                          'click_through': self.click_through.isChecked()}
        if self.duration.value():
            scene.playback['duration'] = self.duration.value()
        self.document.replace_document(scene, 'Edit 3D playback')

    def _scene_settings(self):
        if not self.syncing:
            scene = self.document.scene.copy()
            scene.canvas = (self.canvas_width.value(), self.canvas_height.value())
            self.document.replace_document(scene, 'Resize 3D canvas')

    def _background(self):
        from PySide6.QtGui import QColor
        color = QColorDialog.getColor(QColor.fromRgbF(*self.document.scene.background), self,
            translate('scene3d_background', 'Background'), QColorDialog.ColorDialogOption.ShowAlphaChannel)
        if color.isValid():
            scene = self.document.scene.copy()
            scene.background = list(color.getRgbF())
            self.document.replace_document(scene, 'Change scene background')

    def _color(self):
        from PySide6.QtGui import QColor
        if len(self.selected) != 1:
            return
        entry = self.document.entries[self.selected[0]]
        if entry.get('locked'):
            return
        color = QColorDialog.getColor(QColor.fromRgbF(*entry.get('color', [1, 1, 1])), self)
        if color.isValid():
            self.document.update(self.selected[0], {'color': list(color.getRgbF()[:3])}, 'Change 3D color')

    def control(self, operation):
        if self.runtime:
            if operation == 'replay':
                self.runtime.timeline.play(restart=True)
            else:
                getattr(self.runtime.timeline, operation)()

    def seek(self):
        if self.runtime:
            self.runtime.timeline.pause()
            self.runtime.timeline.seek(self.position.value())
            self.viewport.update()

    def focus(self):
        if self.viewport:
            self.viewport.focus_selection()

    def reset_view(self):
        if self.viewport:
            self.viewport.reset_camera()

    def apply_view(self):
        if not self.viewport or not self.viewport.camera:
            return
        if self.document.entries[self.document.scene.camera].get('locked'):
            self._error('The playback camera is locked')
            return
        entry, matrix = self.viewport.camera
        # Qt extracts a quaternion from a normalized 3x3 orientation.
        from PySide6.QtGui import QQuaternion, QMatrix3x3
        orientation = matrix[:3, :3].copy()
        orientation /= np.linalg.norm(orientation, axis=0)
        q = QQuaternion.fromRotationMatrix(QMatrix3x3(orientation.reshape(-1).tolist()))
        self.document.update(self.document.scene.camera, {'parent': None,
            'projection': entry.get('projection', 'perspective'), 'fov': entry.get('fov', 45),
            'ortho_height': entry.get('ortho_height', 10.8), 'transform': {
                'position': matrix[:3, 3].tolist(), 'rotation': [q.x(), q.y(), q.z(), q.scalar()], 'scale': [1, 1, 1]}},
                'Use editor view as playback camera')

    def add_object(self, kind):
        if kind == 'MODEL':
            path, _ = QFileDialog.getOpenFileName(self, translate('scene3d_add_model', 'Add 3D model'), '', '3D models (*.glb *.gltf *.obj)')
            if not path:
                return
            entry = {'type': kind, 'file_path': path}
        elif kind == 'CAMERA':
            entry = deepcopy(DEFAULT_CAMERA)
        else:
            entry = {'type': kind}
        self.editor._select_layer(self.document.add(entry, 'Add 3D object'))

    def showEvent(self, event):
        if self.runtime:
            self.runtime.set_owner(id(self), True)
        self.timer.start()
        super().showEvent(event)

    def hideEvent(self, event):
        if self.runtime:
            self.runtime.set_owner(id(self), False)
        self.timer.stop()
        super().hideEvent(event)

    def shutdown(self):
        if self.closed:
            return
        self.closed = True
        self.cancel.set()
        self.generation += 1
        self.timer.stop()
        if self.viewport:
            self.viewport.set_runtime(None)
        if self.runtime:
            self.runtime.close()
            self.runtime.deleteLater()
            self.runtime = None
