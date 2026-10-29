"""Render INKSIDE templates and garments into layered-pet v1 folders.

Every part drawing is rendered once per output layer and per rotation, cropped
to its visible pixels and deduplicated by content, so a head reused in forty
frames is one atlas cell positioned by forty layer offsets. Cells are packed
into one atlas per layer kind: a few files instead of hundreds, which matters
because every file open is scanned by antivirus software.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1
import json
from pathlib import Path
from typing import Callable

import numpy
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QImage, QPainter

from frontengine.show.pet.inkside.ink import FIXED, Brush
from frontengine.show.pet.inkside.rig import Pose, timelines

FORMAT = 'frontengine.layered-pet/1'
LICENSE = 'FrontEngine built-in INKSIDE artwork, generated from frontengine/show/pet/inkside (MIT)'
CANVAS = 256
_SCRATCH = 448
ATLAS_SIDE = 2048
_ORIGIN = _SCRATCH // 2


@dataclass(frozen=True)
class Element:
    """One drawing placed on one part for one frame."""
    part: str
    z: int
    draw: Callable[[Brush], None]
    key: tuple
    angle: int = 0
    clip_top: float | None = None
    variant: tuple[str, str] | None = None
    required: bool = False      # emit a transparent placeholder when nothing is drawn


class AssetWriter:
    def __init__(self, folder: Path, colors: dict[str, str]) -> None:
        self.folder = folder
        self.colors = colors
        self._crops: dict[str, tuple[str, QImage]] = {}
        self._cache: dict[tuple, list] = {}

    def _store(self, name: str, image: QImage) -> str:
        """Key a crop by its pixels; identical crops share one atlas cell."""
        image = image.convertToFormat(QImage.Format.Format_ARGB32)
        digest = sha1(bytes(image.constBits()) + f'{image.width()}x{image.height()}'.encode()).hexdigest()[:20]
        key = name + ':' + digest
        self._crops.setdefault(key, (name, image))
        return key

    def layers(self, element: Element) -> list[tuple[str, str, tuple[int, int]]]:
        """(image, layer name, offset from the part pivot) for every layer of a drawing."""
        cache_key = (element.key, element.angle, element.clip_top)
        if cache_key not in self._cache:
            probe = Brush(None, None, self.colors)
            element.draw(probe)
            names = [name for name in probe.used if name != 'ink'] + (['ink'] if 'ink' in probe.used else [])
            rendered = [(name, *self._render(element, name)) for name in names]
            rendered = [entry for entry in rendered if entry[1] is not None]
            if not rendered and (element.variant is not None or element.required):
                # Every part choice needs a layer in every frame, even an empty one.
                blank = QImage(1, 1, QImage.Format.Format_ARGB32)
                blank.fill(Qt.GlobalColor.transparent)
                rendered = [('ink', blank, (0, 0))]
            self._cache[cache_key] = [(self._store(name, image), name, offset) for name, image, offset in rendered]
        return self._cache[cache_key]

    def _render(self, element: Element, layer: str):
        image = QImage(_SCRATCH, _SCRATCH, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(_ORIGIN, _ORIGIN)
        painter.rotate(element.angle)
        if element.clip_top is not None:
            painter.setClipRect(QRectF(-_SCRATCH, -_SCRATCH, 2 * _SCRATCH, _SCRATCH + element.clip_top))
        element.draw(Brush(painter, layer, self.colors))
        painter.end()
        return _crop(image)

    def write(self, manifest: dict) -> None:
        """Pack crops into one atlas per layer kind, then point every layer at its cell."""
        cells = {}
        for group in sorted({name for name, _ in self._crops.values()}):
            keys = sorted((key for key, (name, _) in self._crops.items() if name == group),
                          key=lambda key: -self._crops[key][1].height())
            for index, (atlas, placed) in enumerate(_pack([self._crops[key][1] for key in keys])):
                relative = f'atlas-{group}-{index}.png'
                if not atlas.save(str(self.folder / relative), 'PNG'):
                    raise OSError(f'Could not write {relative}')
                cells.update({key: (relative, rect) for key, rect in zip(keys, placed) if rect is not None})
        for animation in manifest['actions'].values():
            for frame in animation['frames']:
                for layer in frame['layers']:
                    layer['image'], layer['source'] = cells[layer['image']][0], list(cells[layer['image']][1])
        text = json.dumps(manifest, ensure_ascii=False, separators=(',', ':'))
        (self.folder / 'layered-pet.json').write_text(text, encoding='utf-8')


def _pack(images: list[QImage], side: int = ATLAS_SIDE):
    """Shelf-pack tallest-first; yields (atlas, rects) with None for images left to the next atlas."""
    remaining = list(range(len(images)))
    rects: list = [None] * len(images)
    while remaining:
        x = y = shelf = width = 0
        placed, left = [], []
        for index in remaining:
            image = images[index]
            if x + image.width() > side:
                x, y, shelf = 0, y + shelf + 1, 0
            if y + image.height() > side:
                left.append(index)
                continue
            rects[index] = (x, y, image.width(), image.height())
            placed.append(index)
            width = max(width, x + image.width())
            x += image.width() + 1
            shelf = max(shelf, image.height())
        atlas = QImage(max(1, width), max(1, y + shelf), QImage.Format.Format_ARGB32)
        atlas.fill(Qt.GlobalColor.transparent)
        painter = QPainter(atlas)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        for index in placed:
            painter.drawImage(rects[index][0], rects[index][1], images[index])
        painter.end()
        yield atlas, [rects[index] if index in placed else None for index in range(len(images))]
        remaining = left


def _crop(image: QImage):
    view = image.constBits()
    alpha = numpy.frombuffer(view, dtype=numpy.uint8).reshape((image.height(), image.bytesPerLine() // 4, 4))
    visible = alpha[:, :image.width(), 3] > 0
    rows, cols = numpy.nonzero(visible.any(axis=1))[0], numpy.nonzero(visible.any(axis=0))[0]
    if rows.size == 0:
        return None, None
    top, bottom, left, right = int(rows[0]), int(rows[-1]), int(cols[0]), int(cols[-1])
    cropped = image.copy(left, top, right - left + 1, bottom - top + 1)
    return cropped.convertToFormat(QImage.Format.Format_ARGB32), (left - _ORIGIN, top - _ORIGIN)


def frame_points(base: dict, pose: Pose, nudge=None) -> dict[str, tuple[int, int]]:
    points = {}
    for part, (x, y) in base.items():
        dx, dy = pose.offset(part)
        if nudge is not None:
            extra = nudge(part, pose)
            dx, dy = dx + extra[0], dy + extra[1]
        points[part] = (round(x + dx), round(y + dy))
    points['face'] = points['head']
    points['back'] = points['body']
    return points


def frame_layers(writer: AssetWriter, elements: list[Element], points: dict, palette: dict) -> list[dict]:
    result = []
    for element in elements:
        anchor = 'head' if element.part == 'face' else element.part
        for image, name, (ox, oy) in writer.layers(element):
            px, py = points[element.part]
            ax, ay = points[anchor]
            layer = {'image': image, 'z': element.z, 'anchor': anchor, 'offset': [px - ax + ox, py - ay + oy]}
            if name not in FIXED and name in palette:
                layer['tint'] = name
            if element.variant is not None:
                layer['variant'] = list(element.variant)
            result.append(layer)
    return result


def manifest(identifier: str, name: str, kind: str, template: str, slots: list, palette: dict,
             actions: dict, variants: dict | None = None) -> dict:
    data = {'format': FORMAT, 'id': identifier, 'version': '1', 'name': name, 'kind': kind,
            'template': template, 'canvas': [CANVAS, CANVAS], 'slots': slots, 'license': LICENSE,
            'palette': palette, 'actions': actions}
    if variants:
        data['variants'] = variants
    return data


def build_actions(writer: AssetWriter, base: dict, palette: dict, elements_for, nudge=None) -> dict:
    """Run every timeline through ``elements_for(pose) -> list[Element]``."""
    actions = {}
    for action, (loop, poses) in timelines().items():
        frames = []
        for pose in poses:
            points = frame_points(base, pose, nudge)
            anchors = {part: list(point) for part, point in points.items() if part != 'face'}
            frames.append({'duration_ms': pose.duration, 'anchors': anchors,
                           'layers': frame_layers(writer, elements_for(pose), points, palette)})
        actions[action] = {'loop': loop, 'frames': frames}
    return actions
