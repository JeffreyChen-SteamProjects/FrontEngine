"""Turn a generated sprite sheet on flat magenta into aligned, transparent pet frames.

Sheets come from an image model: a grid of equal cells on pure #FF00FF. Keying
removes the background including the anti-aliased fringe (colour is un-mixed
from magenta, not just made transparent), every frame is scaled by one factor so
the character keeps one size, and the feet land on the shared ground line.
"""
from __future__ import annotations

from pathlib import Path

import numpy
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter

MAGENTA = numpy.array([255.0, 0.0, 255.0])


def _rgba(image: QImage) -> numpy.ndarray:
    image = image.convertToFormat(QImage.Format.Format_RGBA8888)
    data = numpy.frombuffer(bytes(image.constBits()), dtype=numpy.uint8)
    return data.reshape((image.height(), image.bytesPerLine() // 4, 4))[:, :image.width()].astype(numpy.float32)


def _image(array: numpy.ndarray) -> QImage:
    data = numpy.ascontiguousarray(array.clip(0, 255).astype(numpy.uint8))
    height, width = data.shape[:2]
    return QImage(data.tobytes(), width, height, width * 4, QImage.Format.Format_RGBA8888).copy()


def key_magenta(array: numpy.ndarray) -> numpy.ndarray:
    """Alpha from how magenta a pixel is; edge colours are un-blended from the background."""
    red, green, blue = array[..., 0], array[..., 1], array[..., 2]
    magenta = numpy.minimum(red, blue) - green
    alpha = numpy.clip(1.0 - (magenta - 40.0) / 150.0, 0.0, 1.0)
    alpha[(red > 200) & (blue > 200) & (green < 90)] = 0.0
    safe = numpy.maximum(alpha, 1e-3)[..., None]
    colour = (array[..., :3] - (1.0 - alpha)[..., None] * MAGENTA) / safe
    out = numpy.empty_like(array)
    out[..., :3] = numpy.clip(colour, 0, 255)
    out[..., 3] = alpha * 255.0
    out[alpha < 0.04] = 0
    return out


def cut_frames(sheet: QImage, columns: int, rows: int) -> list[numpy.ndarray]:
    array = key_magenta(_rgba(sheet))
    height, width = array.shape[0] // rows, array.shape[1] // columns
    return [array[row * height:(row + 1) * height, column * width:(column + 1) * width]
            for row in range(rows) for column in range(columns)]


def _bbox(frame: numpy.ndarray) -> tuple[int, int, int, int]:
    visible = frame[..., 3] > 24
    rows, columns = numpy.nonzero(visible.any(axis=1))[0], numpy.nonzero(visible.any(axis=0))[0]
    return int(columns[0]), int(rows[0]), int(columns[-1]) + 1, int(rows[-1]) + 1


def _head_x(frame: numpy.ndarray, box: tuple[int, int, int, int]) -> float:
    """Horizontal centre of the upper half, where the large stable head is."""
    left, top, right, bottom = box
    upper = frame[top:top + (bottom - top) // 2, left:right, 3] > 24
    columns = numpy.nonzero(upper)[1]
    return left + float(columns.mean()) if columns.size else (left + right) / 2


def _union(boxes: list[tuple[int, int, int, int]]) -> tuple[int, int, int, int]:
    return (min(box[0] for box in boxes), min(box[1] for box in boxes),
            max(box[2] for box in boxes), max(box[3] for box in boxes))


def _placements(frames, boxes, scale, canvas, ground, centre, wall):
    """Top-left of each scaled frame on the canvas."""
    if wall is not None:
        # Climbing hugs the wall: one shared offset keeps the hitch drawn inside the cells.
        _left, _top, right, bottom = _union(boxes)
        return [(wall - (right - box[0]) * scale, ground - (bottom - box[1]) * scale) for box in boxes]
    places = []
    for frame, box in zip(frames, boxes):
        width = (box[2] - box[0]) * scale
        x = min(max(centre - (_head_x(frame, box) - box[0]) * scale, 2), canvas - 2 - width)
        places.append((x, ground - (box[3] - box[1]) * scale))
    return places


def fit_frames(frames: list[numpy.ndarray], canvas: int = 256, height: int = 225, ground: int = 245,
               centre: int = 128, wall: int | None = None) -> list[QImage]:
    """One scale for every frame, standing on ``ground``.

    Generated cells do not share a baseline, so walking frames are aligned one by one:
    the lowest foot on the ground line and the head centred, keeping the gait readable
    without the character jumping between cells. With ``wall`` every frame shares one
    offset that puts the reach of all frames together on that x, for climbing.
    """
    boxes = [_bbox(frame) for frame in frames]
    if wall is not None:
        union = _union(boxes)
        scale = min(height / (union[3] - union[1]), (wall - 4) / (union[2] - union[0]))
    else:
        tallest = max(bottom - top for _left, top, _right, bottom in boxes)
        widest = max(right - left for left, _top, right, _bottom in boxes)
        scale = min(height / tallest, (canvas - 8) / widest)
    out = []
    for frame, box, (x, y) in zip(frames, boxes, _placements(frames, boxes, scale, canvas, ground, centre, wall)):
        left, top, right, bottom = box
        source = _image(frame[top:bottom, left:right])
        width, tall = round((right - left) * scale), round((bottom - top) * scale)
        target = QImage(canvas, canvas, QImage.Format.Format_ARGB32_Premultiplied)
        target.fill(Qt.GlobalColor.transparent)
        painter = QPainter(target)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawImage(round(x), round(y), source.scaled(width, tall, Qt.AspectRatioMode.IgnoreAspectRatio,
                                                                 Qt.TransformationMode.SmoothTransformation))
        painter.end()
        out.append(target)
    return out


SPRITES = Path(__file__).resolve().parent / 'sprites'
_ATLASES: dict[str, QImage] = {}


def write_atlas(frames: list[QImage], name: str, folder: Path = SPRITES) -> Path:
    """Store aligned frames side by side as one PNG shipped with the package."""
    size = frames[0].width()
    atlas = QImage(size * len(frames), size, QImage.Format.Format_ARGB32)
    atlas.fill(Qt.GlobalColor.transparent)
    painter = QPainter(atlas)
    for index, frame in enumerate(frames):
        painter.drawImage(index * size, 0, frame)
    painter.end()
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    if not atlas.save(str(path), 'PNG'):
        raise OSError(f'Could not write {path}')
    return path


def atlas_frame(name: str, index: int) -> QImage:
    """Frame ``index`` of a shipped atlas whose frames are square, side by side."""
    if name not in _ATLASES:
        image = QImage(str(SPRITES / name))
        if image.isNull():
            raise ValueError(f'Missing sprite atlas {name}')
        _ATLASES[name] = image
    atlas = _ATLASES[name]
    size = atlas.height()
    return atlas.copy(index * size, 0, size, size)


def load_sheet(path, columns: int, rows: int, **fit) -> list[QImage]:
    sheet = QImage(str(path))
    if sheet.isNull():
        raise ValueError(f'Could not read sprite sheet {path}')
    return fit_frames(cut_frames(sheet, columns, rows), **fit)
