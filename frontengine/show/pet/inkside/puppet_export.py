"""Export a built-in INKSIDE character as an Imervue .puppet model plus a FrontEngine pet script.

The layered character is composed into one texture per rigged part (tail, feet,
body, arms, head, eye states, mouth states, crown appendages). Rotation
deformers turn the head, arms and tail; a warp moves the whole body; opacity
keys switch eyes and mouth. Motions and expressions are authored on those
parameters, and the script maps FrontEngine companion actions to them.
"""
from __future__ import annotations

import io
import json

from pathlib import Path
import tempfile
import zipfile

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPoint, QRect, Qt
from PySide6.QtGui import QColor, QImage, QPainter

from frontengine.show.pet.inkside.assemble import build_character
from frontengine.show.pet.inkside.library import _template
from frontengine.utils.pet_pack.layered import load_layered_asset

MEDIA_TYPE = 'application/vnd.imervue.puppet+zip'
# Draw order, layer z range and the pose frame each part texture is taken from.
PARTS = (
    ('tail', 10, (0, 14), ('idle', 0)), ('foot_l', 20, (20, 20), ('idle', 0)),
    ('foot_r', 21, (21, 21), ('idle', 0)), ('body', 30, (30, 39), ('idle', 0)),
    ('arm_l', 40, (40, 40), ('idle', 0)), ('arm_r', 42, (42, 42), ('idle', 0)),
    ('head', 50, (45, 56), ('idle', 0)), ('eyes_open', 57, (57, 57), ('idle', 0)),
    ('eyes_closed', 57, (57, 57), ('idle', 3)), ('eyes_happy', 57, (57, 57), ('greet', 0)),
    ('mouth_rest', 58, (58, 58), ('idle', 0)), ('mouth_open', 58, (58, 58), ('feed', 0)),
    ('crown', 66, (60, 70), ('idle', 0)),
)
HEAD_PARTS = ('head', 'eyes_open', 'eyes_closed', 'eyes_happy', 'mouth_rest', 'mouth_open', 'crown')


def _compose(asset, action: str, index: int, z_range: tuple[int, int]) -> QImage:
    """Draw the default-choice layers of one frame whose z lies in the range."""
    frame = asset.actions[action].frames[index]
    defaults = {group: spec['default'] for group, spec in asset.variants.items()}
    canvas = QImage(*asset.canvas, QImage.Format.Format_ARGB32_Premultiplied)
    canvas.fill(Qt.GlobalColor.transparent)
    painter = QPainter(canvas)
    for layer in sorted(frame.layers, key=lambda item: item.z):
        if not z_range[0] <= layer.z <= z_range[1]:
            continue
        if layer.variant is not None and defaults.get(layer.variant[0]) != layer.variant[1]:
            continue
        image = QImage(str(asset.root.joinpath(*layer.image.split('/')))).convertToFormat(
            QImage.Format.Format_ARGB32_Premultiplied)
        if layer.tint is not None:
            tint = QPainter(image)
            tint.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
            tint.fillRect(image.rect(), QColor(asset.palette[layer.tint]))
            tint.end()
        anchor = frame.anchors[layer.anchor] if layer.anchor is not None else (0, 0)
        point = QPoint(anchor[0] + layer.offset[0], anchor[1] + layer.offset[1])
        source = QRect(*layer.source) if layer.source is not None else image.rect()
        painter.drawImage(point, image, source)
    painter.end()
    return canvas


def _png(image: QImage) -> bytes:
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, 'PNG')
    buffer.close()
    return bytes(data.data())


def _drawable(name: str, order: int, size: tuple[int, int]) -> dict:
    w, h = size
    entry = {'id': name, 'texture': f'textures/{name}.png', 'vertices': [[0, 0], [w, 0], [w, h], [0, h]],
             'indices': [0, 1, 2, 0, 2, 3], 'uvs': [[0, 0], [1, 0], [1, 1], [0, 1]], 'draw_order': order}
    keys = {'eyes_open': [('EyeOpen', 0, 1), ('EyeHappy', 1, 0)], 'eyes_closed': [('EyeOpen', 1, 0), ('EyeHappy', 1, 0)],
            'eyes_happy': [('EyeHappy', 0, 1)], 'mouth_rest': [('MouthOpen', 1, 0)], 'mouth_open': [('MouthOpen', 0, 1)]}
    if name in keys:
        entry['opacity_keys'] = [{'parameter': parameter, 'stops': [{'value': 0.0, 'alpha': low},
                                                                     {'value': 1.0, 'alpha': high}]}
                                 for parameter, low, high in keys[name]]
    return entry


def _rig(template, size: tuple[int, int]) -> tuple[list, list]:
    head_x, head_y = template.base['head']
    pivots = {'head_rot': ([head_x, head_y + template.chin], list(HEAD_PARTS)),
              'arm_l_rot': (list(template.base['arm_l']), ['arm_l']),
              'arm_r_rot': (list(template.base['arm_r']), ['arm_r']),
              'tail_rot': (list(template.base['tail']), ['tail'])}
    deformers = [{'id': ident, 'type': 'rotation', 'parent': None, 'drawables': drawables,
                  'form': {'anchor': anchor, 'angle': 0.0}} for ident, (anchor, drawables) in pivots.items()]
    w, h = size
    corners = [[-64.0, -64.0], [w + 64.0, -64.0], [-64.0, h + 64.0], [w + 64.0, h + 64.0]]
    bounds = [-64.0, -64.0, w + 64.0, h + 64.0]
    for ident, drawables in (('body_move', [part[0] for part in PARTS]), ('arm_l_shift', ['arm_l']),
                             ('arm_r_shift', ['arm_r'])):
        deformers.append({'id': ident, 'type': 'warp', 'parent': None, 'drawables': drawables,
                          'form': {'rows': 2, 'cols': 2, 'grid': corners, 'bounds': bounds}})

    def shifted(dx: float, dy: float) -> list:
        return [[x + dx, y + dy] for x, y in corners]

    def angle(ident: str, low: float, high: float) -> list:
        return [{'value': low, 'forms': {ident: {'angle': low}}}, {'value': high, 'forms': {ident: {'angle': high}}}]

    def arm(side: str, sign: int) -> list:
        # As in the sprite rig, a raised arm swings from a lower, wider shoulder so
        # the paw clears the oversized head instead of hiding behind it.
        rot, shift = f'arm_{side}_rot', f'arm_{side}_shift'
        return [{'value': value, 'forms': {rot: {'angle': value}, shift: {'grid': shifted(dx, dy)}}}
                for value, dx, dy in ((-0.5 * sign, 0, 0), (0.0, 0, 0), (1.6 * sign, -14 * sign, 6),
                                      (2.6 * sign, -14 * sign, 6))]

    parameters = [
        {'id': 'AngleZ', 'min': -0.4, 'max': 0.4, 'default': 0.0, 'keys': angle('head_rot', -0.4, 0.4)},
        {'id': 'ArmL', 'min': -0.5, 'max': 2.6, 'default': 0.0, 'keys': arm('l', 1)},
        {'id': 'ArmR', 'min': -2.6, 'max': 0.5, 'default': 0.0, 'keys': list(reversed(arm('r', -1)))},
        {'id': 'Tail', 'min': -0.6, 'max': 0.6, 'default': 0.0, 'keys': angle('tail_rot', -0.6, 0.6)},
        {'id': 'BodyY', 'min': -20.0, 'max': 20.0, 'default': 0.0,
         'keys': [{'value': -20.0, 'forms': {'body_move': {'grid': shifted(0, -20.0)}}},
                  {'value': 20.0, 'forms': {'body_move': {'grid': shifted(0, 20.0)}}}]},
        {'id': 'EyeOpen', 'min': 0.0, 'max': 1.0, 'default': 1.0},
        {'id': 'EyeHappy', 'min': 0.0, 'max': 1.0, 'default': 0.0},
        {'id': 'MouthOpen', 'min': 0.0, 'max': 1.0, 'default': 0.0},
    ]
    return deformers, parameters


def _track(parameter: str, points: list[tuple[float, float]]) -> dict:
    return {'param_id': parameter, 'segments': [
        {'type': 'linear', 'p0': [t0, v0], 'p1': [t1, v1]} for (t0, v0), (t1, v1) in zip(points, points[1:])]}


def _motions() -> dict[str, dict]:
    raise_l, raise_r = 1.9, -1.9
    specs = {
        'idle': (2.4, True, {'BodyY': [(0, 0), (1.2, 2), (2.4, 0)], 'EyeOpen': [(0, 1), (2.15, 1), (2.25, 0), (2.4, 1)]}),
        'walk': (0.56, True, {'BodyY': [(0, 0), (.14, -3), (.28, 0), (.42, -3), (.56, 0)],
                              'ArmL': [(0, .3), (.28, -.3), (.56, .3)], 'ArmR': [(0, .3), (.28, -.3), (.56, .3)]}),
        'wave': (1.2, False, {'ArmR': [(0, 0), (.2, -1.6), (.4, -2.0), (.6, -1.6), (.8, -2.0), (1.2, 0)]}),
        'eat': (1.2, False, {'MouthOpen': [(0, 1), (.3, 0), (.6, 1), (.9, 0), (1.2, 0)],
                             'BodyY': [(0, 0), (.3, 2), (.6, 0), (.9, 2), (1.2, 0)]}),
        'nap': (3.0, True, {'BodyY': [(0, 6), (1.5, 8), (3, 6)]}),
        'sit': (2.0, True, {'BodyY': [(0, 8), (1, 9), (2, 8)]}),
        'celebrate': (1.0, False, {'BodyY': [(0, 0), (.3, -12), (.6, 0), (1, 0)], 'ArmL': [(0, 0), (.3, raise_l), (1, 0)],
                                   'ArmR': [(0, 0), (.3, raise_r), (1, 0)],
                                   'MouthOpen': [(0, 1), (.6, 1), (1, 0)]}),
        'play': (0.9, False, {'BodyY': [(0, 4), (.3, -10), (.6, 0), (.9, 0)], 'ArmL': [(0, .9), (.6, .9), (.9, 0)],
                              'ArmR': [(0, -.9), (.6, -.9), (.9, 0)], 'Tail': [(0, .3), (.45, -.3), (.9, 0)]}),
        'groom': (1.3, False, {'ArmR': [(0, -2.4), (.3, -2.1), (.6, -2.4), (.9, -2.1), (1.3, 0)],
                               'EyeOpen': [(0, 0), (1.2, 0), (1.3, 1)], 'AngleZ': [(0, .1), (.6, -.1), (1.3, 0)]}),
        'pet': (1.2, True, {'AngleZ': [(0, .12), (.6, .06), (1.2, .12)], 'Tail': [(0, .3), (.6, -.3), (1.2, .3)]}),
    }
    # A finished one-shot motion holds its last values, so each must end neutral. Eye
    # states belong to expressions only: Imervue restores a stopped motion's parameters
    # to their pre-motion values, which already include any expression overlay.
    # Without a fade-out, stopping snaps to frame 0; easing back reaches the defaults.
    return {name: {'version': 1, 'duration': duration, 'loop': loop, 'fade_in_duration': 0.15,
                   'fade_out_duration': 0.3,
                   'tracks': [_track(parameter, points) for parameter, points in tracks.items()]}
            for name, (duration, loop, tracks) in specs.items()}


EXPRESSIONS = {'happy': [('EyeHappy', 1.0)], 'sleepy': [('EyeOpen', 0.0)], 'surprised': [('MouthOpen', 1.0)]}
BINDINGS = {
    'greet': {'motion': 'wave', 'expression': 'happy'}, 'peer_greet': {'motion': 'wave'},
    'pet': {'motion': 'pet', 'expression': 'happy'}, 'feed': {'motion': 'eat'}, 'groom': {'motion': 'groom'},
    'play': {'motion': 'play'}, 'celebrate': {'motion': 'celebrate', 'expression': 'happy'},
    'outfit_show': {'motion': 'celebrate', 'expression': 'happy'}, 'catch': {'motion': 'celebrate'},
    'sleep': {'motion': 'nap', 'expression': 'sleepy'}, 'sleep_in': {'motion': 'nap', 'expression': 'sleepy'}, 'wake': {'motion': 'idle'},
    'walk': {'motion': 'walk'}, 'sit': {'motion': 'sit'}, 'food_like': {'expression': 'happy'},
    'food_dislike': {'expression': 'surprised'},
}


def _manifest(template, size: tuple[int, int], motions: dict) -> dict:
    deformers, parameters = _rig(template, size)
    return {'version': 1, 'size': list(size),
            'drawables': [_drawable(name, order, size) for name, order, _z, _frame in PARTS],
            'deformers': deformers, 'parameters': parameters, 'motions': list(motions),
            'expressions': list(EXPRESSIONS),
            'hit_areas': [{'id': 'head', 'drawables': ['head'], 'motion': 'wave'},
                          {'id': 'body', 'drawables': ['body'], 'motion': 'pet'}]}


def export_puppet(identifier: str, folder: str | Path) -> tuple[Path, Path]:
    """Write <identifier>.puppet and <identifier>.petscript.json into folder; return both paths."""
    template = _template(identifier)
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='frontengine-inkside-puppet-') as staging:
        asset = load_layered_asset(build_character(template, Path(staging) / identifier))
        textures = {name: _png(_compose(asset, *frame, z_range)) for name, _order, z_range, frame in PARTS}
    size = tuple(asset.canvas)
    motions = _motions()
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(zipfile.ZipInfo('mimetype'), MEDIA_TYPE, compress_type=zipfile.ZIP_STORED)
        zf.writestr('puppet.json', json.dumps(_manifest(template, size, motions), indent=1))
        for name, data in textures.items():
            zf.writestr(f'textures/{name}.png', data)
        for name, motion in motions.items():
            zf.writestr(f'motions/{name}.json', json.dumps(motion))
        for name, params in EXPRESSIONS.items():
            zf.writestr(f'expressions/{name}.json', json.dumps(
                {'version': 1, 'params': [{'id': key, 'value': value, 'mode': 'overwrite'} for key, value in params]}))
    model = folder / f'{identifier}.puppet'
    model.write_bytes(archive.getvalue())
    script = folder / f'{identifier}.petscript.json'
    script.write_text(json.dumps({'version': 1, 'greetings': [f'{template.name}!'],
                                  'frontengine_actions': BINDINGS}, ensure_ascii=False, indent=1), encoding='utf-8')
    return model, script


__all__ = ['export_puppet', 'BINDINGS']
