"""Bounded layered assets, frame anchors and explicit outfit compatibility."""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
from types import MappingProxyType
from typing import Mapping
from frontengine.utils.pet_pack.palette import checked_palette
from frontengine.utils.pet_pack.variants import checked_groups

SLOTS = ('head', 'neck', 'body', 'back')
ATLAS_SIDE = 2048
ACTIONS = ('idle', 'walk', 'sleep', 'climb', 'fall', 'drag', 'greet', 'pet',
           'feed', 'groom', 'play', 'celebrate', 'outfit_show', 'wake', 'sleep_in', 'food_like', 'food_dislike',
           'sit', 'land', 'peer_greet', 'catch')
_TOKEN = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}')


@dataclass(frozen=True)
class Layer:
    image: str
    z: int
    anchor: str | None
    offset: tuple[int, int]
    tint: str | None = None
    variant: tuple[str, str] | None = None
    source: tuple[int, int, int, int] | None = None


@dataclass(frozen=True)
class Frame:
    duration_ms: int
    anchors: Mapping[str, tuple[int, int]]
    layers: tuple[Layer, ...]


@dataclass(frozen=True)
class Animation:
    loop: bool
    frames: tuple[Frame, ...]

    def frame_index(self, elapsed_ms: int) -> int:
        """Sample every outfit layer from the character's single timeline."""
        if type(elapsed_ms) is not int or elapsed_ms < 0:
            raise ValueError('Animation time must be nonnegative integer milliseconds')
        total = sum(frame.duration_ms for frame in self.frames)
        time = elapsed_ms % total if self.loop else min(elapsed_ms, total - 1)
        for index, frame in enumerate(self.frames):
            if time < frame.duration_ms:
                return index
            time -= frame.duration_ms
        raise AssertionError('Validated animation has no frame')


@dataclass(frozen=True)
class LayeredAsset:
    root: Path
    identifier: str
    version: str
    name: str
    kind: str
    template: str
    canvas: tuple[int, int]
    slots: tuple[str, ...]
    actions: Mapping[str, Animation]
    license: str
    palette: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))
    variants: Mapping = field(default_factory=lambda: MappingProxyType({}))


def _fields(value, fields: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError(f'Invalid {label} fields')


def _token(value) -> str:
    if not isinstance(value, str) or not _TOKEN.fullmatch(value):
        raise ValueError('Invalid layered asset identifier')
    return value


def _integer(value, low: int, high: int) -> int:
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f'Expected integer within {low}..{high}')
    return value


def _pair(value, low: int, high: int) -> tuple[int, int]:
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError('Expected two coordinates')
    return tuple(_integer(item, low, high) for item in value)


def _outer_symlink(root: Path) -> bool:
    return any(parent.is_symlink() for parent in root.parents if parent != root.parent)


def _portable(relative) -> None:
    if (not isinstance(relative, str) or len(relative) > 240 or '\\' in relative
            or ':' in relative or relative.startswith('/')
            or any(part in ('', '.', '..') for part in relative.split('/'))):
        raise ValueError('Unsafe layered image path')


def _regular_files(root: Path) -> frozenset[str]:
    """Regular files reachable inside ``root`` without following any link or junction.

    One directory listing replaces several filesystem calls per image, which
    dominated loading assets with hundreds of images.
    """
    if _outer_symlink(root):
        raise ValueError('Layer images cannot use symlinks')
    resolved = root.resolve()
    found, pending, seen = set(), [(root, '')], 0
    while pending:
        folder, prefix = pending.pop()
        with os.scandir(folder) as entries:
            for entry in entries:
                seen += 1
                if seen > 8192:
                    raise ValueError('Layered asset folder contains too many files')
                if entry.is_symlink() or getattr(entry, 'is_junction', lambda: False)():
                    continue
                if entry.is_dir(follow_symlinks=False):
                    if Path(entry.path).resolve().is_relative_to(resolved):
                        pending.append((Path(entry.path), prefix + entry.name + '/'))
                elif entry.is_file(follow_symlinks=False):
                    found.add(prefix + entry.name)
    return frozenset(found)


def image_path(root: Path, relative: str, trusted_root: Path | None = None) -> Path:
    """Resolve only portable PNG paths inside the selected asset folder.

    ``trusted_root`` is the resolved root of a folder whose outer ancestors were
    already checked, so a load with hundreds of images checks them only once.
    """
    _portable(relative)
    parts = relative.split('/')
    path = root.joinpath(*parts)
    if path.suffix.lower() != '.png' or not path.is_file():
        raise ValueError('Layer image must be an existing PNG')
    if not path.resolve().is_relative_to(trusted_root or root.resolve()):
        raise ValueError('Layer image escapes asset folder')
    inner = (path, *list(path.parents)[:len(parts)])
    if any(parent.is_symlink() for parent in inner) or (trusted_root is None and _outer_symlink(root)):
        raise ValueError('Layer images cannot use symlinks')
    return path


def _layer(value, root: Path, checked: dict) -> Layer:
    optional = set(value).intersection({'tint', 'variant', 'source'}) if isinstance(value, dict) else set()
    _fields(value, {'image', 'z', 'anchor', 'offset'} | optional, 'layer')
    variant = value.get('variant')
    if 'variant' in value:
        if not isinstance(variant, list) or len(variant) != 2:
            raise ValueError('Layer variant needs a group and choice')
        variant = tuple(_token(item) for item in variant)
    if value['image'] not in checked:
        # Many frames reuse one image; it is validated once per load against a
        # single listing of the folder. Anything not listed gets the full check,
        # which reports why it was refused.
        _portable(value['image'])
        if '' not in checked:
            checked[''] = _regular_files(root)
        if value['image'] not in checked[''] or not value['image'].lower().endswith('.png'):
            image_path(root, value['image'])
        checked[value['image']] = True
    anchor = None if value['anchor'] is None else _token(value['anchor'])
    source = _source(value['source']) if 'source' in value else None
    return Layer(value['image'], _integer(value['z'], -100, 100), anchor,
                 _pair(value['offset'], -2048, 2048),
                 _token(value['tint']) if 'tint' in value else None, variant, source)


def _source(value) -> tuple[int, int, int, int]:
    if not isinstance(value, list) or len(value) != 4:
        raise ValueError('Layer source needs x, y, width and height')
    x, y = (_integer(item, 0, ATLAS_SIDE - 1) for item in value[:2])
    width, height = (_integer(item, 1, ATLAS_SIDE) for item in value[2:])
    return x, y, width, height


def image_bounds(asset: 'LayeredAsset') -> dict[str, tuple[tuple[int, int], frozenset]]:
    """Per image: the largest size it may decode to and the source rectangles read from it.

    A whole-image layer must fit the canvas; an atlas used only through source
    rectangles may be up to 2048 pixels a side.
    """
    bounds = {}
    for animation in asset.actions.values():
        for frame in animation.frames:
            for layer in frame.layers:
                limit, rects = bounds.get(layer.image, ((ATLAS_SIDE, ATLAS_SIDE), frozenset()))
                if layer.source is None:
                    limit = (min(limit[0], asset.canvas[0]), min(limit[1], asset.canvas[1]))
                else:
                    rects = rects | {layer.source}
                bounds[layer.image] = (limit, rects)
    return bounds


def check_sources(width: int, height: int, rects) -> None:
    if any(x + w > width or y + h > height for x, y, w, h in rects):
        raise ValueError('Layer source rectangle exceeds its image')


def _frame(value, root: Path, checked: dict) -> Frame:
    _fields(value, {'duration_ms', 'anchors', 'layers'}, 'frame')
    anchors = value['anchors']
    if not isinstance(anchors, dict) or len(anchors) > 32:
        raise ValueError('At most 32 anchors per frame')
    anchors = {_token(key): _pair(point, -2048, 2048) for key, point in anchors.items()}
    layers = value['layers']
    if not isinstance(layers, list) or not 1 <= len(layers) <= 72:
        raise ValueError('Each frame needs 1..72 layers including part alternatives')
    return Frame(_integer(value['duration_ms'], 16, 10000), MappingProxyType(anchors),
                 tuple(_layer(layer, root, checked) for layer in layers))


def _animations(value, root: Path) -> Mapping[str, Animation]:
    if not isinstance(value, dict) or not value or set(value) - set(ACTIONS):
        raise ValueError('Unknown or empty layered actions')
    actions = {}
    checked = {}
    count = 0
    for key, data in value.items():
        _fields(data, {'loop', 'frames'}, 'animation')
        if type(data['loop']) is not bool or not isinstance(data['frames'], list):
            raise ValueError('Invalid animation loop or frames')
        count += len(data['frames'])
        if not 1 <= len(data['frames']) <= 120 or count > 512:
            raise ValueError('Animation exceeds 120 frames/action or 512 frames/asset')
        actions[key] = Animation(data['loop'], tuple(_frame(frame, root, checked) for frame in data['frames']))
    return MappingProxyType(actions)


def load_layered_asset(folder: str | Path) -> LayeredAsset:
    """Read a separate layered-pet.json; legacy pet.json keeps its existing meaning."""
    root = Path(folder).absolute()
    manifest = root / 'layered-pet.json'
    if not root.is_dir() or root.is_symlink() or manifest.is_symlink():
        raise ValueError('Choose a regular layered asset folder')
    with manifest.open('rb') as stream:
        raw = stream.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ValueError('Layered manifest exceeds 1 MiB')
    data = json.loads(raw.decode('utf-8-sig'))
    _fields(data, {'format', 'id', 'version', 'name', 'kind', 'template', 'canvas',
                   'slots', 'actions', 'license'} | (set(data).intersection({'palette', 'variants'}) if isinstance(data, dict) else set()), 'layered asset')
    if data['format'] != 'frontengine.layered-pet/1' or data['kind'] not in ('character', 'garment'):
        raise ValueError('Unsupported layered asset format or kind')
    for key in ('name', 'license'):
        if not isinstance(data[key], str) or not 1 <= len(data[key].strip()) <= 256:
            raise ValueError(f'Invalid asset {key}')
    slots = data['slots']
    if (not isinstance(slots, list) or any(slot not in SLOTS for slot in slots)
            or len(set(slots)) != len(slots)):
        raise ValueError('Invalid or duplicate garment slots')
    if bool(slots) != (data['kind'] == 'garment'):
        raise ValueError('Only garments must declare occupied slots')
    actions = _animations(data['actions'], root)
    palette = checked_palette(data.get('palette', {}))
    groups = checked_groups(data.get('variants', {}))
    if groups and data['kind'] != 'character':
        raise ValueError('Only characters can declare part variants')
    expected = {(group, choice) for group, spec in groups.items() for choice in spec['choices']}
    for animation in actions.values():
        for frame in animation.frames:
            declared = {layer.variant for layer in frame.layers if layer.variant is not None}
            if declared != expected:
                raise ValueError('Every frame must cover exactly the declared character part choices')
    if any(layer.tint is not None and layer.tint not in palette for animation in actions.values()
           for frame in animation.frames for layer in frame.layers):
        raise ValueError('Layer tint references an undeclared palette region')
    canvas = _pair(data['canvas'], 16, 2048)
    if any(layer.source is not None and (layer.source[2] > canvas[0] or layer.source[3] > canvas[1])
           for animation in actions.values() for frame in animation.frames for layer in frame.layers):
        raise ValueError('Layer source rectangles must fit the canvas')
    if data['kind'] == 'character' and 'idle' not in actions:
        raise ValueError('Characters require an idle action')
    return LayeredAsset(root, _token(data['id']), _token(data['version']), data['name'],
                        data['kind'], _token(data['template']), _pair(data['canvas'], 16, 2048),
                        tuple(slots), actions, data['license'], MappingProxyType(palette),
                        MappingProxyType({key: MappingProxyType({**spec, 'choices': MappingProxyType(spec['choices'])})
                                          for key, spec in groups.items()}))


def validate_outfit(character: LayeredAsset, garments: tuple[LayeredAsset, ...]) -> None:
    """Reject incomplete animation coverage, mismatched templates and slot conflicts."""
    if character.kind != 'character' or len(garments) > 4:
        raise ValueError('An outfit needs one character and at most four garments')
    occupied = set()
    for garment in garments:
        if (garment.kind != 'garment' or garment.template != character.template
                or garment.canvas != character.canvas):
            raise ValueError(f'Incompatible garment: {garment.name}')
        if occupied.intersection(garment.slots):
            raise ValueError(f'Garment slots conflict: {garment.name}')
        occupied.update(garment.slots)
        for action, animation in character.actions.items():
            other = garment.actions.get(action)
            if (other is None or other.loop != animation.loop
                    or tuple(f.duration_ms for f in other.frames)
                    != tuple(f.duration_ms for f in animation.frames)):
                raise ValueError(f'{garment.name} lacks matching animation: {action}')
    for action, animation in character.actions.items():
        for index, frame in enumerate(animation.frames):
            layers = frame.layers + tuple(layer for garment in garments
                                          for layer in garment.actions[action].frames[index].layers)
            if any(layer.anchor is not None and layer.anchor not in frame.anchors for layer in layers):
                raise ValueError(f'Unknown character anchor in {action} frame {index}')
