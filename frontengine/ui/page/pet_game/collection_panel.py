"""The Collection tab: every piece of furniture and how to get it, what the pets made, and the photo album."""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QSize, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QIcon, QImage, QPixmap
from PySide6.QtWidgets import QLabel, QPushButton

from frontengine.ui.page.pet_game.goals_panel import ALBUM_FOLDER
from frontengine.ui.page.pet_game.home_things import ThingGrid, thing_icon
from frontengine.utils.multi_language.retranslate import translate, tr
from frontengine.utils.pet_game import goals
from frontengine.utils.pet_game.catalog import FURNITURE_PREFIX

if TYPE_CHECKING:
    from frontengine.ui.page.pet_game.home_page import PetHomePage

MAX_PHOTOS = 24


def owned_count(world, identifier: str) -> int:
    return world.stored(identifier) + sum(1 for piece in world.furniture.values() if piece.definition == identifier)


def how_to_get(world, definition) -> str:
    """One short line: owned, a starter piece, made at a workstation, locked, or its price."""
    owned = owned_count(world, definition.identifier)
    if owned:
        return translate("pet_home_owned", "owned × {count}").format(count=owned)
    if definition.essential:
        return translate("pet_home_starter_piece", "comes with every home")
    if any(FURNITURE_PREFIX + definition.identifier in recipe.outputs for recipe in world.catalog.recipes.values()):
        return translate("pet_home_made_at_station", "made at a workstation")
    if not goals.unlocked(world, definition.unlock_level):
        return translate("pet_home_unlock_level", "home level {level}").format(level=definition.unlock_level)
    return translate("pet_home_price_short", "{price} coins").format(price=definition.price)


def creations(world) -> list[tuple[str, int]]:
    """``(recipe id, units finished)`` for every job, from the home's own counters."""
    return [(identifier, world.progress.stats.get("settled:" + identifier, 0))
            for identifier in world.catalog.recipes]


def album_photos(folder: Path, limit: int = MAX_PHOTOS) -> list[Path]:
    """The newest photos the home took; nothing outside the album folder is listed."""
    if not folder.is_dir():
        return []
    photos = [path for path in folder.glob("*.png") if path.is_file() and path.parent == folder]
    return sorted(photos, key=lambda path: path.stat().st_mtime, reverse=True)[:limit]


class CollectionPanel:
    def __init__(self, page: PetHomePage) -> None:
        self.page = page
        self._thumbnails: dict[tuple[str, float], QIcon] = {}
        section = self.section = page.add_section("pet_home_collection_section", "Collection")
        self.count = QLabel()
        section.add_widget(self.count)
        self.encyclopedia = ThingGrid(rows=3)
        section.add_widget(self.encyclopedia, "pet_home_encyclopedia", "Furniture guide")
        self.made = ThingGrid(rows=1)
        section.add_widget(self.made, "pet_home_creations", "What the pets made")
        self.photos = ThingGrid(rows=1)
        self.photos.setIconSize(QSize(96, 64))
        section.add_widget(self.photos, "pet_home_album", "Album")
        self.open_album = tr(QPushButton(), "pet_home_open_album", "Open the album folder")
        self.open_album.clicked.connect(self._open_album)
        section.add_inline(self.open_album)

    def folder(self) -> Path:
        return self.page.lifetime.storage.directory / ALBUM_FOLDER

    def refresh_lists(self) -> None:
        world, zone = self.page.service.world, self.page.zone
        if world is None:
            return
        theme = world.zones[zone].theme if zone else "warm_home"
        definitions = list(world.catalog.furniture.values())
        owned = sum(1 for definition in definitions if owned_count(world, definition.identifier))
        self.count.setText(translate("pet_home_collection", "Furniture collection: {owned} of {total}")
                           .format(owned=owned, total=len(definitions)))
        self.encyclopedia.set_things([
            (definition.identifier, thing_icon(FURNITURE_PREFIX + definition.identifier, theme),
             translate(definition.label_key, definition.fallback) + " — " + how_to_get(world, definition))
            for definition in definitions])
        self.made.set_things([
            (identifier, thing_icon("recipe:" + identifier),
             translate(world.catalog.recipes[identifier].label_key, world.catalog.recipes[identifier].fallback)
             + " — × " + str(count))
            for identifier, count in creations(world)])
        self.photos.set_things([(str(path), self._thumbnail(path), path.stem) for path in album_photos(self.folder())])

    def _thumbnail(self, path: Path) -> QIcon:
        key = (str(path), path.stat().st_mtime)
        if key not in self._thumbnails:
            image = QImage(str(path))
            pixmap = QPixmap.fromImage(image.scaled(192, 128, Qt.AspectRatioMode.KeepAspectRatio,
                                                    Qt.TransformationMode.SmoothTransformation)) if not image.isNull() else QPixmap()
            self._thumbnails[key] = QIcon(pixmap)
        return self._thumbnails[key]

    def _open_album(self) -> None:
        folder = self.folder()
        folder.mkdir(exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
