"""One scene clock, one decoder per source and CPU poses shared by every view."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import time

import numpy as np
from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QImage, QImageReader

from frontengine.utils.scene_format.scene_3d_document import MEDIA_TYPES, read_scene_document, finite
from .math3d import primitive_mesh, projection, sample_entries, world_matrices, transform_matrix
from .model_asset import Material, Mesh, load_model, MAX_DECODED_BYTES
from frontengine.utils.power_mode.power_mode import normalize_tier, tier_interval, tier_render_scale, scaled_interval


def prepare_models(document, cancel=None):
    result, used = {}, 0
    for entry in document.entries.values():
        if cancel is not None and cancel.is_set():
            return {}
        if entry['type'] in ('MODEL', 'IMAGE', 'GIF'):
            path = str(Path(entry['file_path']).resolve())
            if path not in result:
                if entry['type'] == 'MODEL':
                    result[path] = load_model(path)
                    used += result[path].decoded_bytes
                else:
                    reader = QImageReader(path)
                    size = reader.size()
                    if not reader.canRead() or not 0 < size.width()*size.height() <= 16_777_216:
                        raise ValueError('Scene image is invalid or exceeds 16 megapixels')
                    durations, duration = [], 0.
                    if entry['type'] == 'GIF':
                        from PIL import Image
                        with Image.open(path) as movie:
                            for index in range(movie.n_frames):
                                if index >= 10000:
                                    raise ValueError('Scene GIF exceeds 10000 frames')
                                if cancel is not None and cancel.is_set():
                                    return {}
                                movie.seek(index)
                                duration += max(10, movie.info.get('duration', 100))/1000
                                durations.append(duration)
                    result[path] = {'image': reader.read(), 'durations': durations}
                    used += size.width()*size.height()*4
                if used > MAX_DECODED_BYTES:
                    raise ValueError('Scene decoded models exceed 512 MiB')
            if entry['type'] == 'MODEL' and entry.get('clip') and entry['clip'].get('index', 0) >= len(result[path].clips):
                raise ValueError('Model animation clip does not exist')
    return result


class Scene3DClock(QObject):
    changed = Signal(float)
    seeked = Signal(float)
    state_changed = Signal(str)

    def __init__(self, parent=None, *, clock=time.monotonic):
        super().__init__(parent)
        self.clock = clock
        self.duration, self.position, self.rate = 0., 0., 1.
        self.minimum_duration = 0.
        self.loop, self.active, self.requested, self.previewing = False, False, False, False
        self.state = 'stopped'
        self._anchor = self.clock()
        self.timer = QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self.tick)

    def _state(self, state):
        self.state = state
        self.state_changed.emit(state)

    def play(self, *, restart=False):
        if restart or self.duration and self.position >= self.duration:
            self.position = 0.
        self.requested, self.previewing = True, True
        self._anchor = self.clock()-self.position/self.rate
        self._state('playing' if self.active else 'paused')
        if self.active:
            self.timer.start()
        self.changed.emit(self.position)
        self.seeked.emit(self.position)

    def tick(self):
        if not self.active or not self.requested:
            return
        stamp = max(0, (self.clock()-self._anchor)*self.rate)
        if self.duration:
            stamp = stamp % self.duration if self.loop else min(stamp, self.duration)
        self.position = stamp
        self.changed.emit(stamp)
        if self.duration and not self.loop and stamp >= self.duration:
            self.requested = False
            self.timer.stop()
            self._state('finished')

    def pause(self):
        self.tick()
        self.requested = False
        self.timer.stop()
        self._state('paused')

    def seek(self, seconds):
        finite(seconds, 'Timeline position', 0, 3600)
        self.position = min(seconds, self.duration) if self.duration else seconds
        self.previewing = True
        self._anchor = self.clock()-self.position/self.rate
        self.changed.emit(self.position)
        self.seeked.emit(self.position)

    def set_rate(self, rate):
        finite(rate, 'Playback rate', .1, 4)
        self.tick()
        self.rate = rate
        self._anchor = self.clock()-self.position/self.rate
        self.changed.emit(self.position)

    def set_loop(self, loop):
        if type(loop) is not bool:
            raise ValueError('Loop must be boolean')
        self.loop = loop

    def set_active(self, active):
        if self.active == active:
            return
        if not active:
            self.tick()
        self.active = active
        self.timer.stop()
        self._anchor = self.clock()-self.position/self.rate
        if self.requested:
            self._state('playing' if active else 'paused')
            if active:
                self.timer.start()

    def reset(self):
        self.timer.stop()
        self.position, self.requested, self.previewing = 0., False, False
        self._state('stopped')
        self.changed.emit(0.)

    def shutdown(self):
        self.timer.stop()
        self.requested = False


class MediaSource:
    def __init__(self, entry, preview=False, prepared=None):
        self.entry, self.widget, self.image, self.movie = deepcopy(entry), None, QImage(), None
        self.audition = False
        self._video_stamp = None
        self.durations, self.duration, self.frame_index = [], 0., -1
        kind = entry['type']
        if kind in ('IMAGE', 'GIF'):
            reader = QImageReader(entry['file_path'])
            size = reader.size()
            if not reader.canRead() or not 0 < size.width()*size.height() <= 16_777_216:
                raise ValueError('Scene image exceeds 16 megapixels or cannot be read')
            if kind == 'GIF':
                from PIL import Image
                self.movie = Image.open(entry['file_path'])
                if prepared and prepared.get('durations'):
                    self.durations = prepared['durations']
                    self.duration = self.durations[-1]
                else:
                    for index in range(self.movie.n_frames):
                        if index >= 10000:
                            raise ValueError('Scene GIF exceeds 10000 frames')
                        self.movie.seek(index)
                        self.duration += max(10, self.movie.info.get('duration', 100))/1000
                        self.durations.append(self.duration)
                self.movie.seek(0)
                self.sync(0, False, 1, True)
            else:
                self.image = prepared['image'] if prepared else reader.read()
        else:
            settings = {**entry, 'opacity': 100}
            if kind == 'TEXT':
                from frontengine.show.overlay_factory import build_overlay
                self.widget = build_overlay('text', settings)
                self.widget.set_render_backend('software')
            else:
                from .media_frame import SceneMediaFrame
                self.widget = SceneMediaFrame(settings, preview=preview)
            self.widget.resize(round(entry.get('width', 320)), round(entry.get('height', 180)))
            self.widget.overlay_remembers_geometry = False

    def sync(self, seconds, playing, rate, muted, force=False):
        kind = self.entry['type']
        if self.movie:
            stamp = seconds * self.entry.get('speed', 100)/100
            index = min(len(self.durations)-1, int(np.searchsorted(self.durations, stamp % self.duration, side='right')))
            if index != self.frame_index:
                self.movie.seek(index)
                image = self.movie.convert('RGBA')
                self.image = QImage(image.tobytes(), image.width, image.height, QImage.Format.Format_RGBA8888).copy()
                self.frame_index = index
        if self.widget is None:
            return
        if hasattr(self.widget, 'set_active'):
            self.widget.set_active(playing and self.entry.get('visible', True))
            if kind == 'VIDEO':
                self.widget.timer.stop()  # The shared scene clock polls the one retained sink frame.
        if hasattr(self.widget, 'set_muted'):
            self.widget.set_muted(muted or not playing)
        player = getattr(self.widget, 'media_player', None)
        if player:
            duration = player.duration()
            self.duration = duration/1000
            source_rate = self.entry.get('play_rate', 100)/100
            target = int(seconds*1000*source_rate)
            if duration:
                target %= duration
            player.setPlaybackRate(rate*source_rate)
            if player.isSeekable() and (force or abs(player.position()-target) > 100):
                player.setPosition(target)
            if kind == 'VIDEO':
                self._refresh_video()

    def _refresh_video(self):
        frame = self.widget.sink.videoFrame()
        if frame.isValid():
            stamp = frame.startTime(), frame.endTime()
            if stamp != self._video_stamp or stamp[0] < 0:
                self.widget.set_frame(frame.toImage())
                self._video_stamp = stamp

    def frame(self):
        if self.widget:
            if self.entry['type'] == 'VIDEO':
                self._refresh_video()
            if hasattr(self.widget, 'refresh_frame') and self.widget.frame.isNull():
                self.widget.refresh_frame()
            return self.widget.output_frame()
        return self.image

    def close(self):
        if self.movie:
            self.movie.close()
        if self.widget:
            self.widget.close()
            self.widget.deleteLater()


class Scene3DRuntime(QObject):
    failed = Signal(str)
    performance_changed = Signal(int, float)
    def __init__(self, document, models=None, parent=None, *, preview=False, enable_media=True):
        super().__init__(parent)
        self.document = read_scene_document(document)
        self.models = prepare_models(self.document) if models is None else dict(models)
        self.sources, self.meshes, self.owners = {}, {}, set()
        self.closed, self.muted, self.opacity = False, preview, 1.
        self.preview = preview
        from frontengine.user_setting.user_setting_file import user_setting_dict
        self.quality_tier = normalize_tier(user_setting_dict.get('quality_tier'))
        self.low_power = bool(user_setting_dict.get('low_power', False))
        self.render_scale = 1.
        self.topology = None
        self._sample_stamp, self._sample = None, None
        self._ready_sources = frozenset()
        self.timeline = Scene3DClock(self)
        self.timeline.rate = self.document.playback.get('rate', 1)
        self.timeline.loop = self.document.playback.get('loop', False)
        self.timeline.changed.connect(self._time_changed)
        self.timeline.seeked.connect(lambda seconds: self._time_changed(seconds, force=True))
        self.timeline.state_changed.connect(lambda _state: self._time_changed(self.timeline.position))
        if sum(e['type'] in ('VIDEO', 'WEB', 'PUPPET', 'SOUND') for e in self.document.entries.values()) > 8:
            raise ValueError('3D scenes support at most eight native media sources')
        try:
            pixels = 0
            for key, entry in self.document.entries.items():
                kind = entry['type']
                if preview and not enable_media and kind in ('VIDEO', 'WEB', 'PUPPET', 'SOUND'):
                    continue
                if kind in MEDIA_TYPES:
                    prepared = self.models.get(str(Path(entry['file_path']).resolve())) if kind in ('IMAGE', 'GIF') else None
                    self.sources[key] = MediaSource(entry, preview, prepared)
                    widget = self.sources[key].widget
                    if widget is not None and hasattr(widget, 'failed'):
                        widget.failed.connect(lambda message, layer=key: self.failed.emit(layer+': '+message))
                    pixels += entry.get('width', 320)*entry.get('height', 180)
                if kind in ('CUBE', 'SPHERE', 'PLANE') or kind in MEDIA_TYPES-{'SOUND'}:
                    positions, normals, uv, indices = primitive_mesh(kind if kind in ('CUBE', 'SPHERE') else 'PLANE')
                    self.meshes[key] = Mesh(positions, normals, uv, indices,
                                            Material(color=[*entry.get('color', [.7, .72, .8]), 1],
                                                     roughness=entry.get('roughness', .7), metallic=entry.get('metallic', 0),
                                                     unlit=kind in MEDIA_TYPES, double_sided=kind in MEDIA_TYPES or kind == 'PLANE'))
            if pixels > 16_777_216:
                raise ValueError('Scene media exceeds the 16 megapixel raster budget')
            self._duration()
            self.apply_quality_tier()
        except Exception:
            self.close()
            raise

    def _duration(self):
        duration = 0.
        for entry in self.document.entries.values():
            for frames in entry.get('tracks', {}).values():
                duration = max(duration, frames[-1]['time'])
            if entry.get('animation'):
                duration = max(duration, entry['animation'][-1]['time'])
            if entry['type'] == 'MODEL':
                asset = self.models[str(Path(entry['file_path']).resolve())]
                clip = entry.get('clip', {})
                if asset.clips:
                    duration = max(duration, clip.get('start', 0)+asset.clips[clip.get('index', 0)]['duration']/clip.get('rate', 1))
        for source in self.sources.values():
            source_rate = source.entry.get('speed' if source.movie else 'play_rate', 100)/100
            duration = max(duration, source.duration/max(.001, source_rate))
        self.timeline.duration = max(self.timeline.minimum_duration, self.document.playback.get('duration', min(duration, 3600)))

    def set_owner(self, owner, active):
        self.owners.add(owner) if active else self.owners.discard(owner)
        self.timeline.set_active(bool(self.owners))
        self._time_changed(self.timeline.position)

    def set_quality_tier(self, tier):
        self.quality_tier = normalize_tier(tier)
        self.apply_quality_tier()

    def set_low_power(self, enabled):
        self.low_power = bool(enabled)
        self.apply_quality_tier()

    def apply_quality_tier(self):
        interval = scaled_interval(tier_interval(16, self.quality_tier), self.low_power)
        self.render_scale = tier_render_scale(self.quality_tier)
        self.timeline.timer.setInterval(interval)
        for source in self.sources.values():
            widget = source.widget
            if widget is not None:
                if hasattr(widget, 'set_quality_tier'):
                    widget.set_quality_tier(self.quality_tier)
                if hasattr(widget, 'set_low_power'):
                    widget.set_low_power(self.low_power)
        self.performance_changed.emit(interval, self.render_scale)

    def _time_changed(self, seconds, force=False):
        if self.closed:
            return
        self._sample_stamp = None
        for source in self.sources.values():
            muted = self.muted and not (self.preview and source.audition)
            source.sync(seconds, self.timeline.state == 'playing' and bool(self.owners), self.timeline.rate, muted, force=force)
        self._duration()

    def update_document(self, document):
        document = read_scene_document(document)
        if set(document.entries) != set(self.document.entries):
            return False
        source_fields = ('type', 'file_path', 'url', 'text', 'font_size', 'parameters', 'motion', 'expression', 'volume', 'play_rate', 'speed', 'width', 'height')
        if any(any(entry.get(f) != self.document.entries[key].get(f) for f in source_fields)
               for key, entry in document.entries.items()):
            return False
        for entry in document.entries.values():
            if entry['type'] == 'MODEL' and entry.get('clip'):
                asset = self.models[str(Path(entry['file_path']).resolve())]
                if entry['clip'].get('index', 0) >= len(asset.clips):
                    return False
        self.document = document
        self.timeline.set_rate(document.playback.get('rate', 1))
        self.timeline.set_loop(document.playback.get('loop', False))
        for key, source in self.sources.items():
            source.entry = deepcopy(document.entries[key])
        self._time_changed(self.timeline.position)
        return True

    def render_data(self, camera=None):
        stamp = self.timeline.position
        frames = {key: source.frame() for key, source in self.sources.items() if source.entry['type'] != 'SOUND'}
        ready = frozenset(key for key, image in frames.items() if not image.isNull())
        if ready != self._ready_sources:
            self._sample_stamp, self._ready_sources = None, ready
        if self._sample_stamp != stamp:
            entries = sample_entries(self.document.entries, stamp)
            matrices = world_matrices(entries)
            draws, lights = [], []
            def visible(key):
                entry = entries[key]
                return entry.get('visible', True) and (visible(entry['parent']) if entry.get('parent') else True)
            for key, entry in entries.items():
                if not visible(key):
                    continue
                kind, matrix = entry['type'], matrices[key]
                if kind == 'LIGHT':
                    lights.append((entry.get('light_type', 'directional'), matrix, entry.get('color', [1, 1, 1]), entry.get('intensity', 1)))
                items = []
                if kind == 'MODEL':
                    items = self.models[str(Path(entry['file_path']).resolve())].sample(stamp, entry.get('clip'))
                elif key in self.meshes:
                    mesh = self.meshes[key]
                    mesh.material.color = [*entry.get('color', [1, 1, 1] if kind in MEDIA_TYPES else [.7, .72, .8]), 1]
                    mesh.material.metallic, mesh.material.roughness = entry.get('metallic', 0), entry.get('roughness', .7)
                    if key in self.sources:
                        image = frames[key]
                        if image.isNull():
                            continue
                        mesh.material.alpha_mode = 'BLEND'
                        mesh.material.textures['base'] = {'image': image, 'uv': 0, 'sampler': {'wrapS': 33071, 'wrapT': 33071, 'minFilter': 9729}, 'transform': {}}
                    items = [(mesh, mesh.positions, mesh.normals, np.eye(4))]
                screen = kind in MEDIA_TYPES and entry.get('space', 'screen') == 'screen'
                for mesh, positions, normals, local in items:
                    model = matrix @ local
                    if kind in MEDIA_TYPES:
                        width, height = entry.get('width', 320), entry.get('height', 180)
                        if screen:
                            angle = np.radians(-entry.get('rotation', 0))
                            c, s = np.cos(angle), np.sin(angle)
                            canvas = self.document.canvas
                            # Legacy 2D transforms rotate/scale about the top-left corner.
                            model = np.array([[c, -s, 0, entry.get('x', 0)], [s, c, 0, canvas[1]-entry.get('y', 0)], [0, 0, 1, 0], [0, 0, 0, 1.]])
                            size = transform_matrix({'position': [width*entry.get('scale', 1)/2, -height*entry.get('scale', 1)/2, 0],
                                                     'scale': [width*entry.get('scale', 1), height*entry.get('scale', 1), 1]})
                            model = model @ size
                        else:
                            model = model @ transform_matrix({'scale': [width/100, height/100, 1]})
                    draws.append({'key': key, 'mesh': mesh, 'positions': positions, 'normals': normals, 'matrix': model,
                                  'opacity': entry.get('opacity', 100)/100*self.opacity, 'screen': screen, 'z': entry.get('z', 0)})
            self._sample = entries, matrices, draws, lights
            self._sample_stamp = stamp
        entries, matrices, draws, lights = self._sample
        # Live sources may replace their retained frame without a clock tick.
        for draw in draws:
            source = self.sources.get(draw['key'])
            if source:
                image = frames[draw['key']]
                if not image.isNull():
                    draw['mesh'].material.textures['base']['image'] = image
        camera_entry, camera_matrix = (camera if camera is not None else (entries[self.document.camera], matrices[self.document.camera]))
        width, height = self.document.canvas
        screen_vp = np.array([[2/width, 0, 0, -1], [0, 2/height, 0, -1], [0, 0, -.001, 0], [0, 0, 0, 1.]])
        return {'draws': draws, 'lights': lights, 'vp': projection(camera_entry, width/height) @ np.linalg.inv(camera_matrix),
                'eye': camera_matrix[:3, 3], 'screen_vp': screen_vp}

    def set_muted(self, muted):
        self.muted = bool(muted)
        self._time_changed(self.timeline.position)

    def close(self):
        if self.closed:
            return
        self.closed = True
        if self.topology is not None:
            self.topology.close()
            self.topology = None
        self.timeline.shutdown()
        for source in self.sources.values():
            source.close()
        self.sources.clear()
        self.models.clear()
        self.meshes.clear()
        self.owners.clear()
        self._sample, self._sample_stamp = None, None
