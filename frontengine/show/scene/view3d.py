"""Qt presentation and explicit offscreen output for the shared 3D renderer."""
from __future__ import annotations

from copy import deepcopy
import math

import numpy as np
from OpenGL import GL
from PySide6.QtCore import Qt, QTimer, Signal, QSize, QPointF, QRectF
from PySide6.QtGui import QImage, QOpenGLContext, QOffscreenSurface, QSurfaceFormat, QPainter, QPen, QColor
from PySide6.QtOpenGL import QOpenGLFramebufferObject, QOpenGLFramebufferObjectFormat
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QWidget, QVBoxLayout

from frontengine.show.window_helpers import apply_overlay_window_flags
from .math3d import transform_matrix, euler_quaternion
from .renderer3d import Scene3DRenderer


def surface_format():
    fmt = QSurfaceFormat()
    fmt.setVersion(3, 3)
    fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
    fmt.setRenderableType(QSurfaceFormat.RenderableType.OpenGL)
    fmt.setAlphaBufferSize(8)
    fmt.setDepthBufferSize(24)
    fmt.setStencilBufferSize(8)
    return fmt


class OffscreenScene3D:
    def __init__(self, runtime, size, screen=None):
        self.runtime, self.size = runtime, QSize(*size)
        self.context, self.surface, self.fbo, self.renderer = None, None, None, None
        self.scene_fbo = None
        try:
            self.context = QOpenGLContext()
            if screen is not None:
                self.context.setScreen(screen)
            self.context.setFormat(surface_format())
            if not self.context.create():
                raise RuntimeError('Cannot create an OpenGL 3.3 context')
            self.surface = QOffscreenSurface(screen) if screen else QOffscreenSurface()
            self.surface.setFormat(self.context.format())
            self.surface.create()
            if not self.surface.isValid() or not self.context.makeCurrent(self.surface):
                raise RuntimeError('Cannot create an offscreen OpenGL surface')
            fmt = QOpenGLFramebufferObjectFormat()
            fmt.setAttachment(QOpenGLFramebufferObject.Attachment.CombinedDepthStencil)
            fmt.setInternalTextureFormat(GL.GL_RGBA8)
            self.fbo = QOpenGLFramebufferObject(self.size, fmt)
            if not self.fbo.isValid():
                raise RuntimeError('Cannot allocate the 3D output framebuffer')
            self.renderer = Scene3DRenderer()
            self.renderer.initialize()
            self.context.doneCurrent()
        except Exception:
            self.close()
            raise

    def frame(self):
        data = self.runtime.render_data()
        if not self.context.makeCurrent(self.surface):
            raise RuntimeError('The offscreen OpenGL context was lost')
        try:
            size = QSize(max(1, round(self.size.width()*self.runtime.render_scale)),
                         max(1, round(self.size.height()*self.runtime.render_scale)))
            if size != self.size:
                if self.scene_fbo is None or self.scene_fbo.size() != size:
                    fmt = QOpenGLFramebufferObjectFormat()
                    fmt.setAttachment(QOpenGLFramebufferObject.Attachment.CombinedDepthStencil)
                    fmt.setInternalTextureFormat(GL.GL_RGBA8)
                    self.scene_fbo = QOpenGLFramebufferObject(size, fmt)
                    if not self.scene_fbo.isValid():
                        raise RuntimeError('Cannot allocate the quality-scaled scene framebuffer')
                self.renderer.render(self.runtime, size.width(), size.height(), self.scene_fbo.handle(), data=data,
                                     framebuffer_copies=2)
                GL.glBindFramebuffer(GL.GL_READ_FRAMEBUFFER, self.scene_fbo.handle())
                GL.glBindFramebuffer(GL.GL_DRAW_FRAMEBUFFER, self.fbo.handle())
                GL.glBlitFramebuffer(0, 0, size.width(), size.height(), 0, 0, self.size.width(), self.size.height(),
                                      GL.GL_COLOR_BUFFER_BIT, GL.GL_LINEAR)
            else:
                self.scene_fbo = None
                self.renderer.render(self.runtime, self.size.width(), self.size.height(), self.fbo.handle(), data=data)
            image = self.fbo.toImage().convertToFormat(QImage.Format.Format_RGBA8888_Premultiplied)
            image.setDevicePixelRatio(1)
            return image
        finally:
            self.context.doneCurrent()

    def close(self):
        if self.context and self.surface and self.context.makeCurrent(self.surface):
            if self.renderer:
                self.renderer.close()
            self.renderer, self.fbo, self.scene_fbo = None, None, None
            self.context.doneCurrent()
        if self.surface:
            self.surface.destroy()
        self.surface, self.context = None, None
        self.renderer, self.fbo, self.scene_fbo = None, None, None


class Scene3DViewport(QOpenGLWidget):
    failed = Signal(str)
    ready = Signal()
    selection_changed = Signal(object)
    transform_committed = Signal(object)
    axis_selected = Signal(str)

    def __init__(self, runtime=None, parent=None, *, editing=False):
        super().__init__(parent)
        self.setFormat(surface_format())
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAutoFillBackground(False)
        self.runtime, self.renderer, self.error = runtime, None, ''
        self.editing, self.selected, self.tool, self.axis = editing, [], 'move', 'free'
        self.local, self.snap = False, False
        self.camera, self._drag, self._before, self._mode = None, None, None, None
        self._drag_entries = None
        self.orbit_target = np.zeros(3)
        self.previous_frame, self.transition_seconds, self.transition_fbo = QImage(), .5, None
        self.gizmo_axes = []
        self.setMinimumSize(200, 160)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def initializeGL(self):
        self.context().aboutToBeDestroyed.connect(self.cleanup)
        try:
            self.renderer = Scene3DRenderer()
            self.renderer.initialize()
            self.error = ''
            self.ready.emit()
        except Exception as error:
            self._fail(error)

    def _fail(self, error):
        self.error = str(error)
        self.failed.emit(self.error)

    def paintGL(self):
        if self.renderer is None or self.error:
            GL.glClearColor(0, 0, 0, 0)
            GL.glClear(GL.GL_COLOR_BUFFER_BIT)
            return
        if self.runtime is None:
            GL.glClearColor(.12, .13, .16, 1)
            GL.glClear(GL.GL_COLOR_BUFFER_BIT)
            return
        try:
            data = self.runtime.render_data(self.camera)
            self.makeCurrent()
            ratio = self.devicePixelRatioF()
            width, height = round(self.width()*ratio), round(self.height()*ratio)
            render_width = max(1, round(width*self.runtime.render_scale))
            render_height = max(1, round(height*self.runtime.render_scale))
            blend = min(1, self.runtime.timeline.position/self.transition_seconds)
            transitioning = not self.previous_frame.isNull() and blend < 1
            if transitioning or self.runtime.render_scale < 1:
                if self.transition_fbo is None or self.transition_fbo.size() != QSize(render_width, render_height):
                    fmt = QOpenGLFramebufferObjectFormat()
                    fmt.setAttachment(QOpenGLFramebufferObject.Attachment.CombinedDepthStencil)
                    self.transition_fbo = QOpenGLFramebufferObject(QSize(render_width, render_height), fmt)
                    if not self.transition_fbo.isValid():
                        raise RuntimeError('Cannot allocate a scene transition framebuffer')
                self.renderer.render(self.runtime, render_width, render_height, self.transition_fbo.handle(), selected=self.selected, data=data,
                                     framebuffer_copies=2)
                if transitioning:
                    self.renderer.blend_transition(self.transition_fbo.texture(), self.previous_frame, blend,
                                                   self.defaultFramebufferObject(), width, height)
                else:
                    self.previous_frame = QImage()
                    GL.glBindFramebuffer(GL.GL_READ_FRAMEBUFFER, self.transition_fbo.handle())
                    GL.glBindFramebuffer(GL.GL_DRAW_FRAMEBUFFER, self.defaultFramebufferObject())
                    GL.glBlitFramebuffer(0, 0, render_width, render_height, 0, 0, width, height,
                                          GL.GL_COLOR_BUFFER_BIT, GL.GL_LINEAR)
            else:
                self.previous_frame, self.transition_fbo = QImage(), None
                self.renderer.render(self.runtime, width, height, self.defaultFramebufferObject(), selected=self.selected, data=data)
            if self.editing:
                self._paint_gizmo(data)
        except Exception as error:
            self._fail(error)

    def _paint_gizmo(self, data):
        self.gizmo_axes = []
        if not self.selected or self.selected[0] not in self.runtime.document.entries:
            return
        from .math3d import world_matrices
        entry = self.runtime.document.entries[self.selected[0]]
        from frontengine.utils.scene_format.scene_3d_document import MEDIA_TYPES
        if entry.get('locked') or entry.get('space', 'screen' if entry['type'] in MEDIA_TYPES else 'world') == 'screen':
            return
        matrix = world_matrices(self.runtime.document.entries)[self.selected[0]]
        origin = matrix[:3, 3]
        width, height = self.runtime.document.canvas
        scale = min(self.width()/width, self.height()/height)
        left, top = (self.width()-width*scale)/2, (self.height()-height*scale)/2
        def project(point):
            clip = data['vp'] @ [*point, 1]
            if clip[3] <= 0:
                return None
            clip = clip[:3]/clip[3]
            return QPointF(left+(clip[0]+1)*width*scale/2, top+(1-clip[1])*height*scale/2)
        center = project(origin)
        if center is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for index, color in enumerate(('#ef5350', '#66bb6a', '#42a5f5')):
            basis = matrix[:3, index] if self.local else np.eye(3)[index]
            basis = basis/max(np.linalg.norm(basis), 1e-9)
            endpoint = project(origin+basis)
            if endpoint is None:
                continue
            delta = endpoint-center
            length = math.hypot(delta.x(), delta.y())
            if length < 1:
                continue
            endpoint = center+delta*(65/length)
            painter.setPen(QPen(QColor(color), 3))
            painter.drawLine(center, endpoint)
            if self.tool == 'scale':
                painter.drawRect(QRectF(endpoint.x()-4, endpoint.y()-4, 8, 8))
            else:
                painter.drawEllipse(endpoint, 4, 4)
            painter.drawText(endpoint+QPointF(5, -5), 'XYZ'[index])
            self.gizmo_axes.append(('xyz'[index], center, endpoint))
        painter.end()

    def set_runtime(self, runtime):
        if runtime is self.runtime:
            return
        if self.renderer and self.context() and self.context().isValid():
            self.makeCurrent()
            self.renderer.close()
            self.renderer.initialize()
            self.doneCurrent()
        self.runtime, self.error = runtime, ''
        self.update()

    def output_frame(self):
        if not self.isValid() or self.error:
            raise RuntimeError(self.error or 'OpenGL viewport is not ready')
        return self.grabFramebuffer()

    def cleanup(self):
        if self.renderer and self.context() and self.context().isValid():
            self.makeCurrent()
            self.renderer.close()
            self.transition_fbo = None
            self.doneCurrent()
        self.renderer = None
        self.previous_frame = QImage()

    def reset_camera(self):
        self.camera = None
        self.orbit_target = np.zeros(3)
        self.update()

    def _camera(self):
        if self.camera is None:
            from .math3d import world_matrices
            entry = self.runtime.document.entries[self.runtime.document.camera]
            matrix = world_matrices(self.runtime.document.entries)[self.runtime.document.camera]
            self.camera = deepcopy(entry), matrix.copy()
        return self.camera

    def focus_selection(self):
        if not self.runtime:
            return
        data = self.runtime.render_data(self.camera)
        points = []
        for draw in data['draws']:
            if not draw['screen'] and (not self.selected or draw['key'] in self.selected):
                positions = draw['positions']
                bounds = np.array([positions.min(axis=0), positions.max(axis=0)])
                points.extend((draw['matrix'] @ np.column_stack([bounds, [1, 1]]).T).T[:, :3])
        if points:
            points = np.asarray(points)
            center = (points.min(axis=0)+points.max(axis=0))/2
            radius = max(.2, np.linalg.norm(points.max(axis=0)-points.min(axis=0))/2)
            entry, matrix = self._camera()
            distance = radius/math.tan(math.radians(entry.get('fov', 45))/2)*1.3
            matrix[:3, 3] = center+matrix[:3, 2]*distance
            self.orbit_target = center
            entry['ortho_height'] = float(radius*2.6)
            self.update()

    def pick(self, point):
        if not self.runtime:
            return None
        data = self.runtime.render_data(self.camera)
        canvas = self.runtime.document.canvas
        scale = min(self.width()/canvas[0], self.height()/canvas[1])
        x = (point.x()-(self.width()-canvas[0]*scale)/2)/scale
        y = (point.y()-(self.height()-canvas[1]*scale)/2)/scale
        if not 0 <= x <= canvas[0] or not 0 <= y <= canvas[1]:
            return None
        inverse = np.linalg.inv(data['vp'])
        a = inverse @ [x/canvas[0]*2-1, 1-y/canvas[1]*2, -1, 1]
        b = inverse @ [x/canvas[0]*2-1, 1-y/canvas[1]*2, 1, 1]
        origin, end = a[:3]/a[3], b[:3]/b[3]
        direction = end-origin
        best, distance, screen_z = None, float('inf'), -float('inf')
        for draw in data['draws']:
            if draw['screen']:
                local = np.linalg.inv(draw['matrix']) @ [x, canvas[1]-y, 0, 1]
                if -.5 <= local[0] <= .5 and -.5 <= local[1] <= .5 and draw['z'] >= screen_z:
                    best, screen_z = draw['key'], draw['z']
                continue
            if screen_z != -float('inf'):
                continue
            local = np.linalg.inv(draw['matrix'])
            o = (local @ [*origin, 1])[:3]
            d = (local @ [*direction, 0])[:3]
            positions = draw['positions']
            lo, hi = positions.min(axis=0), positions.max(axis=0)
            valid = True
            tmin, tmax = 0., 1.
            for axis in range(3):
                if abs(d[axis]) < 1e-12:
                    if not lo[axis] <= o[axis] <= hi[axis]:
                        valid = False
                        break
                else:
                    t0, t1 = sorted(((lo[axis]-o[axis])/d[axis], (hi[axis]-o[axis])/d[axis]))
                    tmin, tmax = max(tmin, t0), min(tmax, t1)
            if valid and tmax >= tmin and tmin < distance:
                best, distance = draw['key'], tmin
        return best

    def mousePressEvent(self, event):
        if not self.runtime:
            return
        self._drag = event.position()
        self._mode = 'orbit' if event.button() == Qt.MouseButton.RightButton else 'pan' if event.button() == Qt.MouseButton.MiddleButton else 'object'
        if self._mode == 'object':
            handle = None
            if self.editing:
                for axis, start, end in self.gizmo_axes:
                    vector = end-start
                    delta = event.position()-start
                    length = vector.x()**2+vector.y()**2
                    t = min(1, max(0, (delta.x()*vector.x()+delta.y()*vector.y())/max(1, length)))
                    nearest = start+vector*t
                    if math.hypot(event.position().x()-nearest.x(), event.position().y()-nearest.y()) < 7:
                        handle = axis
                        break
            key = self.selected[0] if handle and self.selected else self.pick(event.position())
            if handle:
                self.axis = handle
                self.axis_selected.emit(handle)
            if self.editing:
                if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                    self.selected = [k for k in self.selected if k != key] if key in self.selected else self.selected+([key] if key else [])
                elif key not in self.selected:
                    self.selected = [key] if key else []
                self.selection_changed.emit(self.selected)
                self._before = deepcopy(self.runtime.document.entries)
                from .math3d import sample_entries
                self._drag_entries = sample_entries(self._before, self.runtime.timeline.position)
        self.update()

    def mouseMoveEvent(self, event):
        if self._drag is None or not self.runtime:
            return
        delta = event.position()-self._drag
        if self._mode in ('orbit', 'pan'):
            entry, matrix = self._camera()
            if self._mode == 'orbit':
                rotation = transform_matrix({'rotation': euler_quaternion([-delta.y()*.3, -delta.x()*.3, 0])})
                u, _, v = np.linalg.svd(matrix[:3, :3])
                basis = u @ v
                world_rotation = basis @ rotation[:3, :3] @ basis.T
                matrix[:3, 3] = self.orbit_target+world_rotation @ (matrix[:3, 3]-self.orbit_target)
                matrix[:3, :3] = world_rotation @ matrix[:3, :3]
            else:
                offset = (-matrix[:3, 0]*delta.x()+matrix[:3, 1]*delta.y())*.015
                matrix[:3, 3] += offset
                self.orbit_target += offset
            self._drag = event.position()
        elif self.editing and self._before is not None and self.runtime.timeline.state != 'playing':
            from .math3d import quaternion_product, world_matrices
            matrices = world_matrices(self._drag_entries)
            for key in self.selected:
                original = self._before[key]
                if original.get('locked'):
                    continue
                parent = original.get('parent')
                while parent is not None and parent not in self.selected:
                    parent = self._before[parent].get('parent')
                if parent in self.selected:
                    continue
                if original.get('space', 'screen' if original['type'] in ('IMAGE', 'GIF', 'TEXT', 'VIDEO', 'WEB', 'PUPPET', 'SOUND') else 'world') == 'screen':
                    if self.tool == 'move':
                        canvas = self.runtime.document.canvas
                        factor = min(self.width()/canvas[0], self.height()/canvas[1])
                        self.runtime.document.entries[key].update(x=original.get('x', 0)+delta.x()/factor,
                                                                  y=original.get('y', 0)+delta.y()/factor)
                    elif self.tool == 'rotate':
                        self.runtime.document.entries[key]['rotation'] = original.get('rotation', 0)+(delta.x()-delta.y())*.5
                    else:
                        self.runtime.document.entries[key]['scale'] = min(100, max(.01, original.get('scale', 1)*(1+(delta.x()-delta.y())*.005)))
                    continue
                transform = deepcopy(self._drag_entries[key]['transform'])
                axis = 'xyz'.find(self.axis)
                if self.tool == 'move':
                    camera = self._camera()[1]
                    move = (camera[:3, 0]*delta.x()-camera[:3, 1]*delta.y())*.015
                    if axis >= 0:
                        basis = matrices[key][:3, axis] if self.local else np.eye(3)[axis]
                        basis = basis/max(np.linalg.norm(basis), 1e-9)
                        move = basis*np.dot(move, basis)
                    if original.get('parent'):
                        move = np.linalg.inv(matrices[original['parent']])[:3, :3] @ move
                    value = np.asarray(transform['position'])+move
                    transform['position'] = (np.round(value*10)/10 if self.snap else value).tolist()
                elif self.tool == 'rotate':
                    degrees = (delta.x()-delta.y())*.5
                    if self.snap:
                        degrees = round(degrees/15)*15
                    basis = np.eye(3)[axis if axis >= 0 else 1]
                    if not self.local and original.get('parent'):
                        u, _, v = np.linalg.svd(matrices[original['parent']][:3, :3])
                        basis = (u @ v).T @ basis
                    angle = math.radians(degrees)/2
                    rotation = [*(basis*math.sin(angle)), math.cos(angle)]
                    transform['rotation'] = (quaternion_product(transform['rotation'], rotation) if self.local else
                                              quaternion_product(rotation, transform['rotation'])).tolist()
                else:
                    value = np.asarray(transform['scale'], dtype=np.float64)
                    factor = max(.01, 1+(delta.x()-delta.y())*.005)
                    if axis < 0:
                        value *= factor
                    else:
                        value[axis] *= factor
                    transform['scale'] = (np.sign(value)*np.maximum(.01, np.round(np.abs(value)*10)/10) if self.snap else value).tolist()
                self.runtime.document.entries[key]['transform'] = transform
                channel = {'move': 'position', 'rotate': 'rotation', 'scale': 'scale3d'}[self.tool]
                self.runtime.document.entries[key].get('tracks', {}).pop(channel, None)
            self.runtime._sample_stamp = None
        self.update()

    def mouseReleaseEvent(self, event):
        if self._before is not None and self.runtime:
            after = deepcopy(self.runtime.document.entries)
            stamp = self.runtime.timeline.position
            for key in self.selected:
                old = self._before[key]
                if 'tracks' in old:
                    after[key]['tracks'] = deepcopy(old['tracks'])
                for channel, name in (('position', 'position'), ('rotation', 'rotation'), ('scale3d', 'scale')):
                    frames = old.get('tracks', {}).get(channel)
                    if frames and after[key]['transform'][name] != self._drag_entries[key]['transform'][name]:
                        values = [frame for frame in frames if abs(frame['time']-stamp) > 1e-6]
                        values.append({'time': stamp, 'value': after[key]['transform'][name]})
                        after[key].setdefault('tracks', {})[channel] = sorted(values, key=lambda frame: frame['time'])
                    if frames:
                        after[key]['transform'][name] = old['transform'][name]
            self.runtime.document.entries = self._before
            self.runtime._sample_stamp = None
            self._before = None
            self.transform_committed.emit(after)
        self._drag, self._mode = None, None
        self._drag_entries = None
        self.update()

    def mouseDoubleClickEvent(self, event):
        if self.runtime:
            key = self.pick(event.position())
            source = self.runtime.sources.get(key)
            if source and source.widget and hasattr(source.widget, 'interact'):
                source.widget.interact()

    def wheelEvent(self, event):
        if self.runtime:
            entry, matrix = self._camera()
            step = event.angleDelta().y()/120
            if entry.get('projection') == 'orthographic':
                entry['ortho_height'] = min(100000, max(.001, entry.get('ortho_height', 10.8)*(.85**step)))
            else:
                distance = matrix[:3, 3]-self.orbit_target
                factor = .85**max(-20, min(20, step))
                if np.linalg.norm(distance)*factor >= .01:
                    matrix[:3, 3] = self.orbit_target+distance*factor
            self.update()


class Scene3DView(QWidget):
    closed = Signal()
    def __init__(self, runtime):
        super().__init__()
        self.runtime, self.timeline, self.opacity = runtime, runtime.timeline, 1.
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        apply_overlay_window_flags(self, allow_input=not runtime.document.playback.get('click_through', False))
        self._priming = False
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.viewport = Scene3DViewport(runtime, self)
        self.viewport.failed.connect(runtime.failed)
        layout.addWidget(self.viewport)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.viewport.update)
        self.runtime.performance_changed.connect(self._performance_changed)
        self._performance_changed(runtime.timeline.timer.interval(), runtime.render_scale)

    @property
    def render_backend(self):
        return 'gpu'

    @property
    def render_failure_reason(self):
        return self.viewport.error

    def apply_quality_tier(self):
        self.runtime.apply_quality_tier()

    def set_quality_tier(self, tier):
        self.runtime.set_quality_tier(tier)

    @property
    def quality_tier(self):
        return self.runtime.quality_tier

    def set_low_power(self, enabled):
        self.runtime.set_low_power(enabled)

    def _performance_changed(self, interval, scale):
        self.timer.setInterval(interval)
        self.viewport.update()

    def set_render_backend(self, backend):
        if backend == 'software':
            self.runtime.failed.emit('3D scenes require OpenGL; select Auto or GPU')

    def set_ui_variable(self, opacity):
        self.opacity = min(1, max(0, opacity))
        self.runtime.opacity = self.opacity
        self.runtime._sample_stamp = None
        self.viewport.update()

    def set_muted(self, muted):
        self.runtime.set_muted(muted)

    def output_frame(self):
        return self.viewport.output_frame()

    def prime(self):
        """Initialize this exact window before the previous playback is replaced."""
        self._priming = True
        self.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
        available = self.screen().availableGeometry().size()
        self.resize(available)
        try:
            self.show()
            frame = self.viewport.grabFramebuffer()
            if frame.isNull() or not self.viewport.isValid() or self.viewport.error:
                raise RuntimeError(self.viewport.error or '3D desktop viewport could not produce its first frame')
        finally:
            self.hide()
            self.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, False)
            self._priming = False

    def begin_transition(self, previous, seconds=.5):
        if previous is not None and not previous.isNull():
            self.viewport.previous_frame = previous.scaled(1920, 1080, Qt.AspectRatioMode.KeepAspectRatio)
            self.viewport.transition_seconds = seconds
            if self.timeline.duration:
                self.runtime.timeline.minimum_duration = max(self.runtime.timeline.minimum_duration, seconds)
            self.runtime._duration()
            self.timeline.play(restart=True)

    def showEvent(self, event):
        if not self._priming:
            self.runtime.set_owner(id(self), True)
            self.timer.start()
        super().showEvent(event)

    def hideEvent(self, event):
        if not self._priming:
            self.runtime.set_owner(id(self), False)
        self.timer.stop()
        super().hideEvent(event)

    def closeEvent(self, event):
        self.runtime.set_owner(id(self), False)
        self.timer.stop()
        self.viewport.cleanup()
        self.closed.emit()
        super().closeEvent(event)
