"""Preloaded RGBA layers sampled together before whole-pet transforms."""
from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QImage, QImageReader, QPainter, QTransform

from frontengine.utils.pet_pack.layered import (
    LayeredAsset, check_sources, image_bounds, image_path, validate_outfit,
)
from frontengine.utils.pet_pack.palette import checked_colors
from frontengine.utils.pet_pack.variants import checked_variants


class LayeredRenderer:
    """One bounded, timer-free outfit renderer usable by a pet or wardrobe preview."""

    def __init__(self, character: LayeredAsset, garments: tuple[LayeredAsset, ...] = (), *, colors=None, variants=None) -> None:
        validate_outfit(character, garments)
        self.character = character
        self.garments = tuple(garments)
        choices = checked_variants({} if variants is None else variants)
        if set(choices) - set(character.variants):
            raise ValueError('Unknown character part group')
        self.variants = {group: choices.get(group, spec['default']) for group, spec in character.variants.items()}
        if any(choice not in character.variants[group]['choices'] for group, choice in self.variants.items()):
            raise ValueError('Unknown character part choice')
        self._palettes = self._resolve_palettes((character, *garments), {} if colors is None else colors)
        self._images = {}
        self._cache_key = None
        self._cache = None
        total_bytes = total_pixels = 0
        loaded_paths = set()
        for asset in (character, *garments):
            paths = {}
            bounds = image_bounds(asset)
            for animation in asset.actions.values():
                for frame in animation.frames:
                    for layer in frame.layers:
                        if layer.image not in paths:
                            paths[layer.image] = image_path(asset.root, layer.image)
                        path = paths[layer.image]
                        color = self._palettes[(asset.identifier, asset.version)].get(layer.tint)
                        key = (path, color)
                        if key in self._images:
                            continue
                        size = path.stat().st_size
                        if path not in loaded_paths:
                            total_bytes += size
                            loaded_paths.add(path)
                        if not 0 < size <= 16 * 1024 * 1024 or total_bytes > 64 * 1024 * 1024:
                            raise ValueError('Outfit image files exceed 16 MiB each or 64 MiB total')
                        limit, rects = bounds[layer.image]
                        image = self._read_image(path, limit)
                        check_sources(image.width(), image.height(), rects)
                        total_pixels += image.width() * image.height()
                        if total_pixels > 16 * 1024 * 1024:
                            raise ValueError('Decoded outfit images exceed 16 megapixels')
                        if color is not None:
                            painter = QPainter(image)
                            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                            painter.fillRect(image.rect(), QColor(color))
                            painter.end()
                        self._images[key] = image

    @staticmethod
    def _resolve_palettes(assets, colors) -> dict:
        overrides = checked_colors(colors)
        known = {asset.identifier + '@' + asset.version for asset in assets}
        if set(overrides) - known:
            raise ValueError('Color override references an unequipped asset')
        palettes = {}
        for asset in assets:
            choices = overrides.get(asset.identifier + '@' + asset.version, {})
            if set(choices) - set(asset.palette):
                raise ValueError('Color override references an undeclared region')
            palettes[(asset.identifier, asset.version)] = {**asset.palette, **choices}
        return palettes

    @staticmethod
    def _read_image(path, canvas) -> QImage:
        # Naming the format skips probing every image plugin; a file that is not
        # really a PNG still fails to decode below.
        reader = QImageReader(str(path), b'png')
        try:
            size = reader.size()
            if (reader.format() != b'png' or not 0 < size.width() <= canvas[0]
                    or not 0 < size.height() <= canvas[1] or reader.supportsAnimation()):
                raise ValueError('Layers must be static PNGs within the declared canvas or atlas size')
            image = reader.read()
            if image.isNull():
                raise ValueError('Could not decode layer image')
            return image.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
        finally:
            device = reader.device()
            if device is not None:
                device.close()

    def render(self, action: str, elapsed_ms: int, *, mirrored: bool = False) -> QImage:
        """Return a detached frame; unknown interaction actions explicitly use idle."""
        action = action if action in self.character.actions else 'idle'
        animation = self.character.actions[action]
        index = animation.frame_index(elapsed_ms)
        key = (action, index, mirrored)
        if key == self._cache_key:
            return self._cache.copy()
        frame = animation.frames[index]
        layers = [(asset, layer) for asset in (self.character, *self.garments)
                  for layer in asset.actions[action].frames[index].layers
                  if layer.variant is None or self.variants.get(layer.variant[0]) == layer.variant[1]]
        image = QImage(*self.character.canvas, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        try:
            for asset, layer in sorted(layers, key=lambda entry: entry[1].z):
                anchor = frame.anchors[layer.anchor] if layer.anchor is not None else (0, 0)
                point = tuple(a + b for a, b in zip(anchor, layer.offset))
                color = self._palettes[(asset.identifier, asset.version)].get(layer.tint)
                path = asset.root.joinpath(*layer.image.split('/'))
                if layer.source is None:
                    painter.drawImage(*point, self._images[(path, color)])
                else:
                    painter.drawImage(QPoint(*point), self._images[(path, color)], QRect(*layer.source))
        finally:
            painter.end()
        if mirrored:
            image = image.transformed(QTransform().scale(-1, 1))
        self._cache_key, self._cache = key, image
        return image.copy()
