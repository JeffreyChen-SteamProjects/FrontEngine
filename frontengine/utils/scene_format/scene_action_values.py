"""Validate portable scene and layer action values without side effects."""
from __future__ import annotations

import json

from frontengine.utils.scene_format.scene_editor_document import validate_geometry


def playback_value(action: str, value: str):
    from frontengine.utils.scene_format.scene_3d_document import finite
    if action in ('scene_pause', 'scene_resume'):
        if value.strip():
            raise ValueError('This playback action does not take a value')
        return None
    data = json.loads(value)
    if action == 'scene_loop':
        if type(data) is not bool:
            raise ValueError('Loop requires true or false')
        return data
    if action == 'scene_seek':
        return finite(data, 'Timeline position', 0, 3600)
    if action == 'scene_rate':
        return finite(data, 'Playback rate', .1, 4)
    raise ValueError('Unknown playback action')


def scene_request(value: str, *, load_only: bool = False) -> tuple[str, str | int]:
    """Accept a path or explicit JSON path/screen; empty playback uses the editor."""
    value = value.strip()
    data = json.loads(value) if value.startswith('{') else {'path': value}
    if not isinstance(data, dict) or set(data) - {'path', 'screen'}:
        raise ValueError('Scene value accepts only path and screen')
    path, screen = data.get('path', ''), data.get('screen', 'primary')
    if not isinstance(path, str) or (load_only and not path.strip()):
        raise ValueError('Loading a scene requires a path')
    if screen not in ('primary', 'all') and (type(screen) is not int or screen < 0):
        raise ValueError('Scene screen must be primary, all or a zero-based index')
    return path, screen


def layer_changes(action: str, value: str) -> tuple[str, dict]:
    """Validate exact layer keys and finite JSON values before any mutation."""
    if action in ('layer_show', 'layer_hide'):
        key, changes = value.strip(), {'visible': action == 'layer_show'}
    else:
        data = json.loads(value)
        if action == 'layer_transform':
            from frontengine.utils.scene_format.scene_3d_document import validate_transform
            if not isinstance(data, dict) or set(data) != {'layer', 'transform'}:
                raise ValueError('3D transform requires layer and transform')
            key = data['layer']
            if not isinstance(key, str) or not key or len(key) > 256:
                raise ValueError('Choose an exact layer key')
            return key, {'transform': validate_transform(data['transform'])}
        expected = {'layer', 'opacity'} if action == 'layer_opacity' else {'layer', 'x', 'y'}
        if not isinstance(data, dict) or set(data) != expected:
            raise ValueError('Layer value must contain layer plus opacity, or layer plus x and y')
        key = data['layer']
        changes = {field: data[field] for field in expected - {'layer'}}
    if not isinstance(key, str) or not key or len(key) > 256:
        raise ValueError('Choose an exact nonempty layer key of at most 256 characters')
    validate_geometry({key: {'type': 'TEXT', **changes}})
    if any(abs(changes.get(field, 0)) > 100000 for field in ('x', 'y')):
        raise ValueError('Layer positions must be between -100000 and 100000')
    return key, changes


