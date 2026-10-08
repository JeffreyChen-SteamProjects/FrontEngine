"""Static resource thumbnails; no media players, scripts, web or pet runtime."""
from __future__ import annotations

import json
from pathlib import Path
import zipfile

from PySide6.QtCore import Qt, QSize, QBuffer, QIODevice, QRectF
from PySide6.QtGui import QImage, QImageReader, QPainter, QColor, QFont

from frontengine.utils.pet_pack.pack_builder import load_pack
from frontengine.utils.imervue.puppet_asset import validate_puppet, checked_members
from frontengine.utils.scene_format.scene_package import load_package
from frontengine.utils.scene_format.scene_editor_document import validate_geometry
from frontengine.utils.scene_format.scene_document import normalize_scene

IMAGE_SUFFIXES = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif'}


def read_json(path: Path, maximum: int = 4 * 1024 * 1024) -> dict:
    """Read bounded JSON without modifying it or accepting symlink targets."""
    if path.is_symlink():
        raise ValueError('Asset document cannot be a symlink')
    with path.open('rb') as stream:
        data = stream.read(maximum + 1)
    if len(data) > maximum:
        raise ValueError('Asset JSON exceeds its size limit')
    result = json.loads(data)
    if not isinstance(result, dict):
        raise ValueError('Asset JSON must be an object')
    return result


def read_image(source: Path | bytes) -> QImage:
    """Decode only one frame, scaled to thumbnail size after checking source bounds."""
    if isinstance(source, Path):
        if source.is_symlink() or source.stat().st_size > 64 * 1024 * 1024:
            raise ValueError('Thumbnail image is linked or exceeds 64 MiB')
        reader = QImageReader(str(source))
        buffer = None
    else:
        if len(source) > 64 * 1024 * 1024:
            raise ValueError('Thumbnail image exceeds 64 MiB')
        buffer = QBuffer()
        buffer.setData(source)
        buffer.open(QIODevice.OpenModeFlag.ReadOnly)
        reader = QImageReader(buffer)
    size = reader.size()
    if size.width() <= 0 or size.height() <= 0 or size.width() * size.height() > 16_777_216:
        raise ValueError('Thumbnail image is invalid or exceeds 16 megapixels')
    reader.setScaledSize(size.scaled(QSize(240, 160), Qt.AspectRatioMode.KeepAspectRatio))
    image = reader.read()
    if buffer is not None:
        buffer.close()
    if image.isNull():
        raise ValueError('Thumbnail image could not be decoded')
    return image.scaled(240, 160, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)


def read_scene(path: Path) -> tuple[dict, object]:
    """Validate scene layers and retain portable extraction only for the caller's thumbnail."""
    lease = None
    if path.suffix.lower() == '.fescene':
        entries, lease = load_package(path)
    else:
        entries = normalize_scene(read_json(path), path.parent)
    try:
        entries = validate_geometry(entries)
        if len(entries) > 256:
            raise ValueError('Asset scene exceeds 256 layers')
        allowed = {'IMAGE', 'GIF', 'TEXT', 'VIDEO', 'WEB', 'SOUND', 'PUPPET'}
        if any(entry.get('type') not in allowed for entry in entries.values()):
            raise ValueError('Asset scene contains an unsupported layer type')
        return entries, lease
    except Exception:
        if lease is not None:
            lease.cleanup()
        raise


def scene_thumbnail(entries: dict) -> QImage:
    """Compose static image/text layer geometry; other media remains a labelled placeholder."""
    image = QImage(240, 160, QImage.Format.Format_RGBA8888_Premultiplied)
    image.fill(QColor('#20252b'))
    painter = QPainter(image)
    painter.setFont(QFont('Sans', 8))
    bounds = QRectF(0, 0, 1920, 1080)
    for entry in entries.values():
        bounds = bounds.united(QRectF(entry.get('x', 0), entry.get('y', 0),
                                     entry.get('width', 320), entry.get('height', 180)))
    scale = min(240 / bounds.width(), 160 / bounds.height())
    painter.scale(scale, scale)
    painter.translate(-bounds.x(), -bounds.y())
    try:
        for entry in sorted(entries.values(), key=lambda entry: entry.get('z', 0)):
            if not entry.get('visible', True):
                continue
            painter.save()
            try:
                painter.translate(entry.get('x', 0), entry.get('y', 0))
                painter.rotate(entry.get('rotation', 0))
                painter.scale(entry.get('scale', 1), entry.get('scale', 1))
                painter.setOpacity(entry.get('opacity', 100) / 100)
                _paint_entry(painter, entry)
            finally:
                painter.restore()
    finally:
        painter.end()
    return image


def _paint_entry(painter: QPainter, entry: dict) -> None:
    rectangle = QRectF(0, 0, entry.get('width', 320), entry.get('height', 180))
    source = Path(entry.get('file_path') or '.')
    if entry['type'] in ('IMAGE', 'GIF') and source.is_file():
        try:
            painter.drawImage(rectangle, read_image(source))
            return
        except (OSError, ValueError):
            pass
    painter.fillRect(rectangle, QColor('#435466'))
    painter.setPen(QColor('#ffffff'))
    painter.drawText(rectangle, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
                     str(entry.get('text', entry['type']))[:1000])


def inspect_asset(path: str | Path) -> tuple[str, QImage]:
    """Classify and thumbnail a user-selected resource without ever starting playback."""
    path = Path(path).absolute()
    if path.is_symlink() or not path.exists():
        raise ValueError('Asset is missing or linked')
    if path.is_dir():
        draft = load_pack(path)
        return 'pet', read_image(Path(next(iter(draft.actions.values()))))
    if path.stat().st_size > 256 * 1024 * 1024:
        raise ValueError('Asset exceeds 256 MiB')
    if path.suffix.lower() in IMAGE_SUFFIXES:
        return ('gif' if path.suffix.lower() == '.gif' else 'image'), read_image(path)
    if path.suffix.lower() == '.puppet':
        manifest = validate_puppet(path)
        with zipfile.ZipFile(path) as archive:
            members = checked_members(archive)
            textures = [entry['texture'] for entry in manifest['drawables']]
            if not textures or members[textures[0]].file_size > 64 * 1024 * 1024:
                raise ValueError('Puppet thumbnail texture is missing or too large')
            return 'puppet', read_image(archive.read(textures[0]))
    if path.suffix.lower() in ('.json', '.fescene'):
        entries, lease = read_scene(path)
        try:
            return 'scene', scene_thumbnail(entries)
        finally:
            if lease is not None:
                lease.cleanup()
    raise ValueError('Choose image/GIF, sprite pet folder, .puppet or scene JSON/.fescene')
