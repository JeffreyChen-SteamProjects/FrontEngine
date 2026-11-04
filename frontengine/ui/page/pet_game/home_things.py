"""Pictures for everything the home lists: furniture, items and jobs, shown as a grid of tiles.

Furniture uses its Blender picture in the zone's theme, items and jobs use the
Blender item icons (``show/pet_game/items``). A tile is the picture, the name and
one short caption (a price, a count, progress).
"""
from __future__ import annotations

from functools import lru_cache

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QIcon, QImage, QPainter, QPixmap
from PySide6.QtWidgets import QListView, QListWidget, QListWidgetItem

from frontengine.show.pet_game.furniture_art import item_picture, picture
from frontengine.utils.pet_game.catalog import FURNITURE_PREFIX

ROLE_KEY = Qt.ItemDataRole.UserRole
TILE_ICON = 64
# A job without an output of its own shows what it makes.
RECIPE_ICONS = {"letter": "letter", "story": "story", "herbs": "herb", "flowers": "flower", "toy": "toy",
                "stool": FURNITURE_PREFIX + "stool", "novel": "novel", "bouquet": "bouquet",
                "music_box": "music_box"}


def _fit(image: QImage | None, size: int) -> QPixmap:
    """The picture centred on a square transparent tile, aspect kept; an empty tile without one."""
    tile = QImage(size * 2, size * 2, QImage.Format.Format_ARGB32_Premultiplied)
    tile.fill(Qt.GlobalColor.transparent)
    if image is not None and not image.isNull():
        scale = min(tile.width() / image.width(), tile.height() / image.height())
        width, height = image.width() * scale, image.height() * scale
        painter = QPainter(tile)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawImage(QRectF((tile.width() - width) / 2, tile.height() - height, width, height), image)
        painter.end()
    result = QPixmap.fromImage(tile)
    result.setDevicePixelRatio(2.0)
    return result


@lru_cache(maxsize=256)
def thing_pixmap(key: str, theme: str = "warm_home", size: int = TILE_ICON) -> QPixmap:
    """``furniture:<id>`` / a furniture id, an item id, or ``recipe:<id>`` as a square picture."""
    if key.startswith("recipe:"):
        key = RECIPE_ICONS.get(key.removeprefix("recipe:"), "coin")
    if key.startswith(FURNITURE_PREFIX):
        return _fit(picture(theme, key.removeprefix(FURNITURE_PREFIX)), size)
    image = item_picture(key)
    if image is None:
        image = picture(theme, key)
    return _fit(image, size)


def thing_icon(key: str, theme: str = "warm_home") -> QIcon:
    return QIcon(thing_pixmap(key, theme))


def tile_text(text: str) -> str:
    """Name on the first line, price or count on the second, so neither is cut off in a tile."""
    return text.replace(" — ", "\n", 1)


class ThingGrid(QListWidget):
    """Tiles that wrap to the width; keeps the selection when refilled."""

    def __init__(self, rows: int = 2) -> None:
        super().__init__()
        self.setObjectName("thingGrid")
        self.setViewMode(QListView.ViewMode.IconMode)
        self.setResizeMode(QListView.ResizeMode.Adjust)
        self.setMovement(QListView.Movement.Static)
        self.setWrapping(True)
        self.setWordWrap(True)
        self.setUniformItemSizes(True)
        self.setIconSize(QSize(TILE_ICON, TILE_ICON))
        self.setGridSize(QSize(132, 128))
        self.setSpacing(4)
        self.setMinimumHeight(128 * rows + 12)
        self.setMaximumHeight(128 * rows + 12)

    def set_things(self, things: list[tuple[str, QIcon, str]]) -> None:
        """``(key, icon, text)`` tiles; the selected key stays selected if it is still there."""
        current = self.current_key()
        things = [(key, icon, tile_text(text)) for key, icon, text in things]
        if [self.item(row).data(ROLE_KEY) for row in range(self.count())] == [key for key, _i, _t in things]:
            for row, (_key, icon, text) in enumerate(things):
                item = self.item(row)
                if item.text() != text:
                    item.setText(text)
                item.setIcon(icon)
                item.setToolTip(text.replace("\n", " "))
            return
        self.clear()
        for key, icon, text in things:
            item = QListWidgetItem(icon, text)
            item.setToolTip(text.replace("\n", " "))
            item.setData(ROLE_KEY, key)
            item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
            self.addItem(item)
            if key == current:
                self.setCurrentItem(item)

    def current_key(self) -> str | None:
        item = self.currentItem()
        return item.data(ROLE_KEY) if item is not None and item.isSelected() else None

    def select_key(self, key: str) -> bool:
        for row in range(self.count()):
            if self.item(row).data(ROLE_KEY) == key:
                self.setCurrentRow(row)
                return True
        return False
