"""Versioned scene documents. Legacy entry dictionaries remain a supported API."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import math
from pathlib import Path

from .scene_document import SCENE_FORMAT, normalize_scene, scene_envelope

MEDIA_TYPES = {'IMAGE', 'GIF', 'TEXT', 'VIDEO', 'WEB', 'PUPPET', 'SOUND'}
OBJECT_TYPES = MEDIA_TYPES | {'MODEL', 'PLANE', 'CUBE', 'SPHERE', 'CAMERA', 'LIGHT', 'GROUP'}
DEFAULT_CAMERA = {'type': 'CAMERA', 'projection': 'perspective', 'fov': 45,
                  'near': .01, 'far': 1000, 'ortho_height': 10.8,
                  'transform': {'position': [0, 0, 13.04]}}
TRACKS = {'position': 3, 'rotation': 4, 'scale3d': 3, 'opacity': 1,
          'fov': 1, 'intensity': 1, 'color': 3}


def finite(value, label, low=-100000, high=100000):
    if type(value) not in (float, int) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f'{label} must be finite and within {low}–{high}')
    return value


def vector(value, count, label):
    if not isinstance(value, (list, tuple)) or len(value) != count:
        raise ValueError(f'{label} requires {count} components')
    result = [finite(item, label) for item in value]
    if count == 4 and sum(item * item for item in result) < 1e-12:
        raise ValueError(f'{label} quaternion must not be zero')
    return result


def validate_transform(value):
    if not isinstance(value, dict) or set(value) - {'position', 'rotation', 'scale'}:
        raise ValueError('Transform accepts position, quaternion rotation and scale')
    result = deepcopy(value)
    for name, count, default in (('position', 3, [0, 0, 0]), ('rotation', 4, [0, 0, 0, 1]),
                                  ('scale', 3, [1, 1, 1])):
        result[name] = vector(result.get(name, default), count, name)
    if any(abs(item) < .00001 for item in result['scale']):
        raise ValueError('3D scale must not be zero')
    return result


def validate_tracks(tracks):
    if not isinstance(tracks, dict) or set(tracks) - TRACKS.keys():
        raise ValueError('Unknown 3D animation track')
    for channel, frames in tracks.items():
        if not isinstance(frames, list) or not 1 <= len(frames) <= 128:
            raise ValueError('A track requires 1–128 keyframes')
        previous = -1
        for frame in frames:
            if not isinstance(frame, dict) or set(frame) - {'time', 'value', 'easing'}:
                raise ValueError('Invalid 3D keyframe')
            stamp = finite(frame.get('time'), 'Keyframe time', 0, 3600)
            if stamp <= previous:
                raise ValueError('Keyframe times must be unique and increasing')
            previous = stamp
            if frame.get('easing', 'linear') not in ('linear', 'smooth', 'step'):
                raise ValueError('Unknown keyframe easing')
            count = TRACKS[channel]
            if count == 1:
                finite(frame.get('value'), channel, *( (0, 100) if channel == 'opacity' else
                       (.1, 179) if channel == 'fov' else (0, 100000)))
            else:
                vector(frame.get('value'), count, channel)
                if channel == 'scale3d' and any(abs(v) < .00001 for v in frame['value']):
                    raise ValueError('Animated scale must not be zero')
    return deepcopy(tracks)


@dataclass
class SceneDocument:
    entries: dict = field(default_factory=dict)
    mode: str = '2d'
    canvas: tuple[int, int] = (1920, 1080)
    camera: str | None = None
    playback: dict = field(default_factory=lambda: {'rate': 1., 'loop': False})
    background: list = field(default_factory=lambda: [0, 0, 0, 0])

    def copy(self):
        return deepcopy(self)

    def envelope(self, base_dir=None):
        if self.mode == '2d':
            return scene_envelope(self.entries, base_dir)
        entries = scene_envelope(self.entries, base_dir)['entries']
        return {'format': SCENE_FORMAT, 'version': 2, 'mode': '3d', 'entries': entries,
                'canvas': list(self.canvas), 'camera': self.camera,
                'playback': deepcopy(self.playback), 'background': list(self.background)}


def read_scene_document(data, base_dir: Path | None = None) -> SceneDocument:
    if isinstance(data, SceneDocument):
        if data.mode not in ('2d', '3d'):
            raise ValueError('Scene mode must be 2d or 3d')
        data = data.envelope()
    if not isinstance(data, dict):
        raise ValueError('A scene must be a JSON object')
    if data.get('format') != SCENE_FORMAT or data.get('version') != 2:
        return SceneDocument(normalize_scene(data, base_dir))
    if type(data['version']) is not int:
        raise ValueError('Scene version must be an integer')
    if set(data) - {'format', 'version', 'mode', 'entries', 'canvas', 'camera', 'playback', 'background'}:
        raise ValueError('Unknown scene v2 fields')
    if data.get('mode') != '3d':
        raise ValueError('Scene v2 requires mode 3d')
    entries = normalize_scene(data.get('entries'), base_dir)
    from .scene_editor_document import validate_geometry
    entries = validate_geometry(entries)
    if len(entries) > 256:
        raise ValueError('Scenes support at most 256 objects')
    for key, entry in entries.items():
        if not isinstance(key, str) or not key or len(key) > 256:
            raise ValueError('Object keys require 1–256 characters')
        kind = entry.get('type')
        if not isinstance(kind, str) or kind not in OBJECT_TYPES:
            raise ValueError(f'Unsupported 3D object type: {kind}')
        entry['transform'] = validate_transform(entry.get('transform', {}))
        validate_tracks(entry.get('tracks', {}))
        if entry.get('space', 'screen' if kind in MEDIA_TYPES else 'world') not in ('world', 'screen'):
            raise ValueError('Object space must be world or screen')
        if kind not in MEDIA_TYPES and entry.get('space', 'world') != 'world':
            raise ValueError('Only media can use screen space')
        for name in ('visible', 'locked'):
            if name in entry and type(entry[name]) is not bool:
                raise ValueError(f'{name} must be boolean')
        finite(entry.get('opacity', 100), 'Opacity', 0, 100)
        if entry.get('parent') is not None and (not isinstance(entry['parent'], str) or entry['parent'] not in entries or entry['parent'] == key):
            raise ValueError('Invalid scene parent')
        if kind == 'MODEL':
            if Path(entry.get('file_path', '')).suffix.lower() not in ('.glb', '.gltf', '.obj'):
                raise ValueError('Choose a GLB, glTF or OBJ model')
            clip = entry.get('clip', {})
            if not isinstance(clip, dict) or set(clip) - {'index', 'start', 'rate', 'loop'}:
                raise ValueError('Invalid model animation clip')
            if type(clip.get('index', 0)) is not int or clip.get('index', 0) < 0:
                raise ValueError('Clip index must be a nonnegative integer')
            finite(clip.get('start', 0), 'Clip start', 0, 3600)
            finite(clip.get('rate', 1), 'Clip rate', .1, 4)
            if type(clip.get('loop', True)) is not bool:
                raise ValueError('Clip loop must be boolean')
        if kind == 'CAMERA':
            if entry.get('projection', 'perspective') not in ('perspective', 'orthographic'):
                raise ValueError('Unknown camera projection')
            near = finite(entry.get('near', .01), 'Near plane', .0001, 10000)
            finite(entry.get('far', 1000), 'Far plane', near + .0001, 100000)
            finite(entry.get('fov', 45), 'Field of view', .1, 179)
            finite(entry.get('ortho_height', 10.8), 'Orthographic height', .001, 100000)
        if kind == 'LIGHT':
            if entry.get('light_type', 'directional') not in ('directional', 'point'):
                raise ValueError('Unknown light type')
            finite(entry.get('intensity', 1), 'Light intensity', 0, 100000)
        if 'color' in entry:
            if any(not 0 <= v <= 1 for v in vector(entry['color'], 3, 'Color')):
                raise ValueError('Color components must be within 0–1')
        for name, low, high, default in (('metallic', 0, 1, 0), ('roughness', .045, 1, .7)):
            if name in entry:
                finite(entry[name], name, low, high)
        seen, parent = {key}, entry.get('parent')
        while parent is not None:
            if not isinstance(parent, str) or parent in seen or parent not in entries:
                raise ValueError('Scene hierarchy contains a cycle or missing parent')
            seen.add(parent)
            parent = entries[parent].get('parent')
    canvas = data.get('canvas', [1920, 1080])
    if not isinstance(canvas, (tuple, list)) or len(canvas) != 2 or any(
            type(v) is not int or not 16 <= v <= 8192 for v in canvas):
        raise ValueError('Canvas requires two dimensions within 16–8192')
    camera = data.get('camera')
    if not isinstance(camera, str) or camera not in entries or entries[camera]['type'] != 'CAMERA':
        raise ValueError('Choose an existing playback camera')
    if sum(entry['type'] == 'LIGHT' for entry in entries.values()) > 8:
        raise ValueError('A 3D scene supports at most eight lights')
    playback = data.get('playback', {})
    if not isinstance(playback, dict) or set(playback) - {'rate', 'loop', 'duration', 'click_through'}:
        raise ValueError('Invalid playback settings')
    finite(playback.get('rate', 1), 'Playback rate', .1, 4)
    if type(playback.get('loop', False)) is not bool:
        raise ValueError('Playback loop must be boolean')
    if type(playback.get('click_through', False)) is not bool:
        raise ValueError('Click-through must be boolean')
    if 'duration' in playback:
        finite(playback['duration'], 'Duration', .001, 3600)
    raw_background = data.get('background', [0, 0, 0, 0])
    if not isinstance(raw_background, (list, tuple)) or len(raw_background) != 4:
        raise ValueError('Background requires four RGBA components')
    background = [finite(v, 'Background', 0, 1) for v in raw_background]
    if any(not 0 <= v <= 1 for v in background):
        raise ValueError('Background components must be within 0–1')
    return SceneDocument(entries, '3d', tuple(canvas), camera, deepcopy(playback), background)


def make_3d_scene(entries=None) -> SceneDocument:
    objects = deepcopy(entries or {})
    key = 'camera'
    while key in objects:
        key += '_'
    objects[key] = deepcopy(DEFAULT_CAMERA)
    light = 'light'
    while light in objects:
        light += '_'
    objects[light] = {'type': 'LIGHT', 'light_type': 'directional', 'intensity': 1,
                      'transform': {'rotation': [-.25, -.3, 0, .92]}}
    return read_scene_document(SceneDocument(objects, '3d', camera=key))
