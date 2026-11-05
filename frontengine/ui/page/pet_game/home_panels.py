"""Panels of the Pet home page: residents, furniture, shop and work.

Panels never change the world themselves; every action goes through
``HomeService.run`` so it is saved and published like any other command.
"""
from __future__ import annotations

from frontengine.ui.page.wrapping_buttons import WrappingCheckBox as QCheckBox, WrappingPushButton as QPushButton

import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from frontengine.ui.runtime_lifetime import owned_action

from PySide6.QtWidgets import QComboBox, QFileDialog, QLabel, QListWidget, QListWidgetItem, QProgressBar
from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QGuiApplication

from frontengine.show.pet_game.captions import (
    NEED_KEYS, activity_text, friends_text, item_label, traits_text, wish_text,
)
from frontengine.utils.pet_game.arrangement import (
    PRESETS, LayoutHistory, apply_layout, decode_layout, encode_layout, plan,
)
from frontengine.ui.page.pet_game.blueprint_dialog import BlueprintVisit
from frontengine.utils.pet_game.blueprint import MAX_BLUEPRINT_BYTES, export_blueprint, visit_blueprint
from frontengine.ui.page.pet_game.home_things import ROLE_KEY, ThingGrid, thing_icon, thing_pixmap
from frontengine.utils.multi_language.retranslate import retranslator, translate, tr
from frontengine.user_setting.user_setting_file import user_setting_dict
from frontengine.utils.pet_game import goals
from frontengine.utils.pet_game.catalog import FURNITURE_PREFIX
from frontengine.utils.pet_game.layout import AREA_TAGS, THEMES
from frontengine.utils.pet_game.world import COMMANDS

if TYPE_CHECKING:
    from frontengine.ui.page.pet_game.home_page import PetHomePage

ROLE_ID = Qt.ItemDataRole.UserRole
PASTED = "pasted"
FOCUS_KEY = "pet_home_focus_companion"


def furniture_name(world, definition: str) -> str:
    found = world.catalog.furniture[definition]
    return translate(found.label_key, found.fallback)


def _button(key: str, fallback: str, callback) -> QPushButton:
    button = tr(QPushButton(), key, fallback)
    button.clicked.connect(callback)
    return button


class ResidentPanel:
    """Moving pets in and out, the selected resident's card and direct commands."""

    def __init__(self, page: PetHomePage) -> None:
        self.page = page
        self.lifetime = page.lifetime
        section = self.section = page.add_section("pet_home_residents_section", "Residents")
        self.profiles = QComboBox()
        section.add_row("pet_home_adopt_label", self.profiles, "Saved pet")
        section.add_inline(_button("pet_home_adopt", "Move in", self.adopt),
                           _button("pet_home_new_resident", "New pet", self.new_pet))
        self.list = QListWidget()
        self.list.setMaximumHeight(110)
        self.list.currentItemChanged.connect(self._list_changed)
        section.add_widget(self.list, "pet_home_resident_label", "Resident")
        self.activity = QLabel()
        self.activity.setWordWrap(True)
        section.add_widget(self.activity)
        self.bars = {}
        for need, key, fallback in NEED_KEYS:
            bar = QProgressBar()
            bar.setRange(0, 100)
            self.bars[need] = bar
            section.add_row(key, bar, fallback)
        self.character = QLabel()
        self.character.setWordWrap(True)
        section.add_widget(self.character)
        self.commands = [_button("pet_home_cmd_" + command, command.title(),
                                 lambda _checked=False, c=command: self.command(c)) for command in COMMANDS]
        section.add_inline(*self.commands)
        section.add_inline(_button("pet_home_wardrobe", "Wardrobe…", self.wardrobe),
                           _button("pet_home_release", "Move out", self.release))
        self.zone_target = QComboBox()
        self.zone_button = _button("pet_home_move_to_zone", "Move to that zone", self.move_to_zone)
        self.zone_row = section.add_inline(self.zone_target, self.zone_button)
        self.wardrobes: dict = {}

    def refresh_lists(self) -> None:
        world = self.page.service.world
        self.profiles.clear()
        living = set(world.residents) if world else set()
        for record in self.page.profiles.profiles():
            if record["id"] not in living:
                self.profiles.addItem(record["name"], record["id"])
        selected = self.page.selected_resident
        self.list.blockSignals(True)
        self.list.clear()
        for resident in sorted(world.residents.values(), key=lambda r: (r.name, r.identifier)) if world else ():
            item = QListWidgetItem(resident.name)
            item.setData(ROLE_ID, resident.identifier)
            self.list.addItem(item)
            if resident.identifier == selected:
                self.list.setCurrentItem(item)
        self.list.blockSignals(False)
        self.zone_target.clear()
        for zone in (world.zones.values() if world else ()):
            self.zone_target.addItem(zone.screen, zone.identifier)
        self.zone_row.setVisible(self.zone_target.count() > 1)

    @owned_action
    def move_to_zone(self) -> None:
        resident, zone = self.page.selected_resident, self.zone_target.currentData()
        if resident and zone:
            self.page.report(self.page.service.run(lambda world: world.transfer_resident(resident, zone)))
            self.page.refresh()

    def refresh_live(self) -> None:
        world = self.page.service.world
        resident = world.residents.get(self.page.selected_resident) if world else None
        for control in (*self.bars.values(), *self.commands):
            control.setEnabled(resident is not None)
        if resident is None:
            self.activity.setText(translate("pet_home_pick_resident", "Pick a resident to see what it is doing."))
            self.character.setText("")
            return
        for need, bar in self.bars.items():
            bar.setValue(resident.needs[need])
        self.activity.setText(activity_text(resident, world))
        lines = (traits_text(resident), friends_text(world, resident), wish_text(world, resident))
        self.character.setText("\n".join(line for line in lines if line))

    def _list_changed(self, current, _previous) -> None:
        if current is not None:
            self.page.select_resident(current.data(ROLE_ID))

    @owned_action
    def command(self, command: str) -> None:
        resident = self.page.selected_resident
        if resident:
            self.page.report(self.page.service.run(lambda world: world.command(resident, command)))

    @owned_action
    def adopt(self) -> None:
        identifier = self.profiles.currentData()
        if identifier:
            self.page.report(self.page.service.adopt(identifier))
            self.page.refresh()
            self.page.select_resident(identifier)

    @owned_action
    def new_pet(self) -> None:
        record = self.page.profiles.create()
        self.page.report(self.page.service.adopt(record["id"]))
        self.page.refresh()
        self.page.select_resident(record["id"])

    @owned_action
    def wardrobe(self) -> None:
        """The existing wardrobe; applying goes through the home's own lease on this pet."""
        identifier = self.page.selected_resident
        if not identifier:
            self.page.report("pick_resident")
            return
        dialog = self.wardrobes.get(identifier)
        if dialog is None:
            from frontengine.show.pet.asset_library import PetAssetLibrary
            from frontengine.ui.dialog.pet_wardrobe import PetWardrobeDialog
            library = PetAssetLibrary(self.lifetime.storage.directory / 'pet-assets')
            dialog = PetWardrobeDialog(self.page.profiles, identifier, self.page, library=library)
            dialog.destroyed.connect(lambda _obj=None, key=identifier: self.wardrobes.pop(key, None))
            self.wardrobes[identifier] = dialog
        dialog.show()
        dialog.raise_()

    @owned_action
    def release(self) -> None:
        resident = self.page.selected_resident
        if resident:
            self.page.report(self.page.service.release(resident))
            self.page.select_resident(None)


class LayoutPanel:
    """Furniture: storage as pictures; placing finds a free spot, arranging places where you click."""

    def __init__(self, page: PetHomePage) -> None:
        self.page = page
        self.lifetime = page.lifetime
        self.arranging = False
        section = self.section = page.add_section("pet_home_layout_section", "Furniture")
        self.theme = QComboBox()
        self.theme.activated.connect(self._theme_chosen)
        section.add_row("pet_home_theme", self.theme, "Theme")
        self.storage = ThingGrid(rows=1)
        self.storage.itemSelectionChanged.connect(self.update_preview)
        self.storage.itemDoubleClicked.connect(lambda _item: self.place())
        section.add_widget(self.storage, "pet_home_storage", "In storage")
        self.place_button = _button("pet_home_place", "Place", self.place)
        self.arrange = _button("pet_home_arrange", "Arrange", self.toggle_arrange)
        section.add_inline(self.place_button, self.arrange)
        self.hint = tr(QLabel(), "pet_home_arrange_hint",
                       "Click the floor to choose a position. Esc stops arranging.")
        self.hint.setWordWrap(True)
        section.add_widget(self.hint)
        self.selected = QLabel()
        self.selected.setWordWrap(True)
        section.add_row("pet_home_selected_furniture", self.selected, "Selected")
        self.actions = [_button("pet_home_flip", "Mirror", self.mirror),
                        _button("pet_home_store", "Put away", self.store),
                        _button("pet_home_assign_bed", "Give bed to resident", self.assign_bed)]
        self.upgrade_button = _button("pet_home_upgrade_station", "Upgrade", self.upgrade)
        self.actions.append(self.upgrade_button)
        section.add_inline(*self.actions)
        self.hint.setVisible(False)
        self.preview_cell: int | None = None
        self._history_world = None
        self._histories: dict[str | None, LayoutHistory] = {}
        self.undo_button = _button("pet_home_undo", "Undo", self.undo)
        self.redo_button = _button("pet_home_redo", "Redo", self.redo)
        self.copy_button = _button("pet_home_copy_layout", "Copy layout", self.copy_layout)
        self.paste_button = _button("pet_home_paste_layout", "Paste layout", self.paste_layout)
        section.add_inline(self.undo_button, self.redo_button, self.copy_button, self.paste_button)
        self.share_button = _button("pet_home_share_blueprint", "Share blueprint…", self.share_blueprint)
        self.visit_button = _button("pet_home_visit_blueprint", "Visit a blueprint…", self.visit_blueprint)
        section.add_inline(self.share_button, self.visit_button)
        self.visits: list = []
        self.presets = QComboBox()
        self.presets.currentIndexChanged.connect(self._preview_layout)
        section.add_row("pet_home_layouts", self.presets, "Ready-made layout")
        self.layout_note = QLabel()
        self.layout_note.setWordWrap(True)
        section.add_widget(self.layout_note)
        self.apply_layout_button = _button("pet_home_apply_layout", "Apply layout", self.apply_layout)
        section.add_inline(self.apply_layout_button)
        self.area_tag = QComboBox()
        self.area_tag.currentIndexChanged.connect(self._area_tool_changed)
        self.area_paint = _button("pet_home_paint_areas", "Paint areas", self._area_tool_changed)
        self.area_paint.setCheckable(True)
        section.add_row("pet_home_area", self.area_tag, "Area")
        section.add_inline(self.area_paint)
        self.zone_screens = QComboBox()
        self.zone_add = _button("pet_home_add_zone", "Add a zone on that screen", self.add_zone)
        self.zone_move = _button("pet_home_move_zone", "Move this zone there", self.move_zone)
        section.add_row("pet_home_other_screen", self.zone_screens, "Other screen")
        section.add_inline(self.zone_add, self.zone_move)
        self.crossing = QComboBox()
        self.crossing.activated.connect(self.link_zone)
        section.add_row("pet_home_crossing", self.crossing, "Entrance leads to")
        self._pasted: list | None = None

    def refresh_lists(self) -> None:
        world, zone = self.page.service.world, self.page.zone
        theme = world.zones[zone].theme if world is not None and zone else "warm_home"
        things = []
        for definition in (world.catalog.furniture if world is not None else ()):
            count = world.stored(definition)
            if world.sandbox or count:
                label = furniture_name(world, definition)
                if not world.sandbox:
                    label = translate("pet_home_stack", "{name} × {count}").format(name=label, count=count)
                things.append((definition, thing_icon(FURNITURE_PREFIX + definition, theme), label))
        self.storage.set_things(things)
        if world is not None:
            self.theme.clear()
            for name in THEMES:
                self.theme.addItem(translate("pet_game_theme_" + name, name), name)
            for name, definition in sorted(world.catalog.themes.items()):     # from content packs
                self.theme.addItem(definition.name, name)
            self.theme.setCurrentIndex(self.theme.findData(theme))
        self.place_button.setEnabled(bool(things))
        self._refresh_presets(world)
        self._refresh_zones()
        self.undo_button.setEnabled(self.history.can_undo())
        self.redo_button.setEnabled(self.history.can_redo())
        self._refresh_selected()
        self.update_preview()

    def _refresh_zones(self) -> None:
        self.area_tag.blockSignals(True)
        current = self.area_tag.currentData()
        self.area_tag.clear()
        for tag in (*AREA_TAGS, "clear"):
            self.area_tag.addItem(translate("pet_home_area_" + tag, tag), tag)
        self.area_tag.setCurrentIndex(max(0, self.area_tag.findData(current)))
        self.area_tag.blockSignals(False)
        screens = self.page.free_screens()
        self.zone_screens.clear()
        for screen in screens:
            self.zone_screens.addItem(screen.name() or "primary", screen)
        for widget in (self.zone_screens, self.zone_add, self.zone_move):
            widget.setEnabled(bool(screens))
        world, zone = self.page.service.world, self.page.zone
        self.crossing.clear()
        self.crossing.addItem(translate("pet_home_crossing_none", "Nowhere (pets stay in this zone)"), None)
        for other in (world.zones.values() if world is not None else ()):
            if other.identifier != zone:
                self.crossing.addItem(other.screen, other.identifier)
        link = world.zones[zone].link if world is not None and zone in world.zones else None
        self.crossing.setCurrentIndex(max(0, self.crossing.findData(link)))
        self.crossing.setEnabled(self.crossing.count() > 1)

    @owned_action
    def link_zone(self, *_args) -> None:
        zone, other = self.page.zone, self.crossing.currentData()
        if zone is not None:
            self.page.report(self.page.service.run(lambda world: world.link_zones(zone, other)))
            self.page.refresh()

    @owned_action
    def _area_tool_changed(self, *_args) -> None:
        tag = self.area_tag.currentData()
        self.page.view.area_tool = tag if self.area_paint.isChecked() else None

    @owned_action
    def paint_area(self, first: int, last: int) -> None:
        tag, zone = self.area_tag.currentData(), self.page.zone
        if zone is not None:
            self.page.report(self.page.service.run(
                lambda world: world.set_area(zone, first, last, None if tag == "clear" else tag)))
            self.page.refresh()

    @owned_action
    def add_zone(self) -> None:
        screen = self.zone_screens.currentData()
        if screen is not None:
            self.page.add_zone(screen)

    @owned_action
    def move_zone(self) -> None:
        screen = self.zone_screens.currentData()
        if screen is not None:
            self.page.move_zone(screen)

    def _refresh_presets(self, world) -> None:
        current = self.presets.currentData()
        self.presets.blockSignals(True)
        self.presets.clear()
        for key in PRESETS:
            self.presets.addItem(translate("pet_home_layout_" + key, key), key)
        if self._pasted is not None:
            self.presets.addItem(translate("pet_home_layout_pasted", "Pasted layout"), PASTED)
        self.presets.setCurrentIndex(max(0, self.presets.findData(current)))
        self.presets.blockSignals(False)
        self.apply_layout_button.setEnabled(world is not None)
        self._preview_layout()

    def _refresh_selected(self) -> None:
        world = self.page.service.world
        piece = world.furniture.get(self.page.selected_furniture) if world else None
        self.selected.setText(furniture_name(world, piece.definition) if piece else
                              translate("pet_home_nothing_selected", "Click a piece of furniture"))
        for button in self.actions:
            button.setEnabled(piece is not None)
        cost = world.upgrade_cost(piece.definition) if piece is not None else None
        self.upgrade_button.setEnabled(cost is not None)
        self.upgrade_button.setText(translate("pet_home_upgrade", "Upgrade ({cost} coins)").format(cost=cost)
                                    if cost is not None else translate("pet_home_upgrade_station", "Upgrade"))

    @owned_action
    def upgrade(self) -> None:
        world = self.page.service.world
        piece = world.furniture.get(self.page.selected_furniture) if world else None
        if piece is not None:
            transaction = "upgrade-" + uuid.uuid4().hex
            self.page.report(self.page.service.run(lambda w: w.upgrade(piece.definition, transaction)))
            self.page.refresh()

    @owned_action
    def _theme_chosen(self, _index: int) -> None:
        theme, zone = self.theme.currentData(), self.page.zone
        if theme and zone:
            self.page.report(self.page.service.run(lambda world: world.set_theme(zone, theme)))
            thing_pixmap.cache_clear()
            self.page.refresh()

    # ----- whole-zone changes -----------------------------------------------------------------

    @property
    def history(self) -> LayoutHistory:
        world = self.page.service.world
        if world is not self._history_world:
            self._histories.clear()
            self._history_world = world
        zone = self.page.zone
        if zone not in self._histories:
            self._histories[zone] = LayoutHistory()
        return self._histories[zone]

    def _change(self, command):
        """Every layout change goes through here so it can be undone."""
        world, zone = self.page.service.world, self.page.zone
        if world is None or zone is None:
            return None
        self.history.record(world, zone)
        result = self.page.service.run(command)
        self.page.refresh()
        return result

    @owned_action
    def undo(self) -> None:
        zone = self.page.zone
        if zone and self.history.can_undo():
            restored = self.page.service.run(lambda world: self.history.undo(world, zone))
            self.page.report("accepted" if restored else "layout_restore_blocked")
            self.page.refresh()

    @owned_action
    def redo(self) -> None:
        zone = self.page.zone
        if zone and self.history.can_redo():
            restored = self.page.service.run(lambda world: self.history.redo(world, zone))
            self.page.report("accepted" if restored else "layout_restore_blocked")
            self.page.refresh()

    @owned_action
    def copy_layout(self) -> None:
        world, zone = self.page.service.world, self.page.zone
        if world is not None and zone:
            QGuiApplication.clipboard().setText(encode_layout(world, zone))
            self.page.report("layout_copied")

    @owned_action
    def paste_layout(self) -> None:
        world = self.page.service.world
        if world is None:
            return
        try:
            self._pasted = decode_layout(QGuiApplication.clipboard().text(), world.catalog)
        except (ValueError, TypeError):
            self.page.report("layout_invalid")
            return
        index = self.presets.findData(PASTED)
        if index < 0:
            self.presets.addItem(translate("pet_home_layout_pasted", "Pasted layout"), PASTED)
            index = self.presets.count() - 1
        self.presets.setCurrentIndex(index)
        self._preview_layout()

    def _chosen_layout(self):
        key = self.presets.currentData()
        return self._pasted if key == PASTED else PRESETS.get(key)

    def _preview_layout(self, *_args) -> None:
        world, zone, pieces = self.page.service.world, self.page.zone, self._chosen_layout()
        if world is None or zone is None or pieces is None:
            self.layout_note.setText("")
            return
        missing, cost, unavailable = plan(world, zone, pieces)
        if not missing:
            text = translate("pet_home_layout_ready", "Everything it needs is in the home or in storage.")
        else:
            names = ", ".join(f"{furniture_name(world, name)} × {count}" for name, count in sorted(missing.items()))
            text = translate("pet_home_layout_missing", "Needs {items} — {cost} coins").format(items=names, cost=cost)
            if unavailable:
                text += " · " + translate("pet_home_layout_unavailable", "some cannot be bought yet and are left out")
        self.layout_note.setText(text)

    @owned_action
    def apply_layout(self) -> None:
        pieces, zone = self._chosen_layout(), self.page.zone
        if pieces is None or zone is None:
            return
        result = self._change(lambda world: apply_layout(world, zone, pieces, "layout-" + uuid.uuid4().hex,
                                                          buy_missing=True))
        if result is not None:
            code, skipped = result
            self.page.report(code if code != "accepted" or not skipped else "layout_partly")
            self._preview_layout()

    # ----- blueprints: the whole home as a file, and a look at someone else's ------------------

    def choose_save_path(self) -> str:
        path, _filter = QFileDialog.getSaveFileName(self.page, translate("pet_home_share_blueprint", "Share blueprint…"),
                                                    "home-blueprint.json", "JSON (*.json)")
        return path

    def choose_open_path(self) -> str:
        path, _filter = QFileDialog.getOpenFileName(self.page, translate("pet_home_visit_blueprint", "Visit a blueprint…"),
                                                    "", "JSON (*.json)")
        return path

    @owned_action
    def share_blueprint(self) -> Path | None:
        """Only rooms and furniture go into the file: no pets, names, coins or anything personal."""
        world = self.page.service.world
        path = self.lifetime.after_dialog(self.choose_save_path()) if world is not None else ""
        if not path:
            return None
        target = Path(path)
        try:
            target.write_text(export_blueprint(world), encoding="utf-8")
        except OSError as error:
            self.page.report_text(str(error))
            return None
        self.page.report_message("pet_home_blueprint_saved", "Blueprint saved to {path}", path=target)
        return target

    @owned_action
    def visit_blueprint(self, path: str | None = None):
        """Open a blueprint read-only (a Workshop item passes its file); a file that is not one is refused."""
        path = self.lifetime.after_dialog(path or self.choose_open_path())
        if not path:
            return None
        source = Path(path)
        try:
            with source.open("rb") as stream:
                raw = stream.read(MAX_BLUEPRINT_BYTES + 1)
            world, missing = visit_blueprint(raw.decode("utf-8"), self.page.service.store.catalog)
        except (OSError, ValueError, UnicodeDecodeError) as error:
            self.page.report_message("pet_home_blueprint_invalid", "That file is not a home blueprint ({error}).",
                                     error=str(error))
            return None
        dialog = BlueprintVisit(world, missing, source.stem, self.page)
        dialog.finished.connect(lambda _code, d=dialog: self.visits.remove(d) if d in self.visits else None)
        self.visits.append(dialog)
        dialog.show()
        return dialog

    @owned_action
    def drag_hover(self, identifier: str, cell: int) -> None:
        world, zone = self.page.service.world, self.page.zone
        piece = world.furniture.get(identifier) if world else None
        if piece is not None and zone:
            problem = world.preview(piece.definition, zone, cell, moving=identifier)
            self.page.set_preview((piece.definition, cell, piece.flipped, problem))

    @owned_action
    def drop(self, identifier: str, cell: int) -> None:
        self.page.set_preview(None)
        world = self.page.service.world
        piece = world.furniture.get(identifier) if world else None
        if piece is None or piece.cell == cell:
            return
        self.page.report(self._change(lambda w: w.move(identifier, cell, None)))

    @owned_action
    def nudge(self, steps: int) -> bool:
        """Arrow keys while arranging: the selected piece moves one cell at a time."""
        world, identifier = self.page.service.world, self.page.selected_furniture
        piece = world.furniture.get(identifier) if world and identifier else None
        if piece is None:
            return False
        self.page.report(self._change(lambda w: w.move(identifier, piece.cell + steps, None)))
        return True

    @owned_action
    def toggle_arrange(self) -> None:
        self.arranging = not self.arranging
        retranslator.set_text(self.arrange, "pet_home_arrange_done" if self.arranging else "pet_home_arrange",
                              "Done arranging" if self.arranging else "Arrange")
        self.hint.setVisible(self.arranging)
        self.preview_cell = None
        self.page.set_arranging(self.arranging)
        self.page.view.drag_enabled = self.arranging
        self.update_preview()

    @owned_action
    def update_preview(self, *_args) -> None:
        """While arranging, the chosen piece shows at the last clicked spot with the reason it would not fit."""
        world, zone = self.page.service.world, self.page.zone
        definition = self.storage.current_key()
        if not self.arranging or world is None or zone is None or definition is None or self.preview_cell is None:
            self.page.set_preview(None)
            return
        problem = world.preview(definition, zone, self.preview_cell)
        self.page.set_preview((definition, self.preview_cell, False, problem))

    @owned_action
    def cell_clicked(self, cell: int) -> None:
        """Arranging: a stored piece goes where you click, or the selected piece moves there."""
        if not self.arranging:
            return
        self.preview_cell = cell
        definition, piece = self.storage.current_key(), self.page.selected_furniture
        if definition is not None:
            self.update_preview()
            if self.page.view.preview is not None and self.page.view.preview[3] is not None:
                self.page.report(self.page.view.preview[3])
                return
            self._place_at(definition, cell)
        elif piece:
            self.page.report(self._change(lambda world: world.move(piece, cell, None)))

    def _place_at(self, definition: str, cell: int | None) -> None:
        zone = self.page.zone
        if cell is None:
            result, identifier = self._change(lambda world: world.place_anywhere(definition, zone))
        else:
            result, identifier = self._change(lambda world: world.place(definition, zone, cell))
        self.page.report(result)
        if identifier:
            self.page.selected_furniture = identifier
            self.preview_cell = None
        self.page.refresh()

    @owned_action
    def place(self) -> None:
        """Put the chosen stored piece in the first free spot."""
        definition = self.storage.current_key() or (self.storage.item(0).data(ROLE_KEY) if self.storage.count() else None)
        if definition and self.page.zone:
            self._place_at(definition, None)

    @owned_action
    def mirror(self) -> None:
        world, piece = self.page.service.world, self.page.selected_furniture
        found = world.furniture.get(piece) if world and piece else None
        if found is not None:
            self.page.report(self._change(lambda w: w.move(piece, found.cell, not found.flipped)))

    @owned_action
    def store(self) -> None:
        piece = self.page.selected_furniture
        if piece:
            self.page.selected_furniture = None
            self.page.report(self._change(lambda world: world.store(piece)))

    @owned_action
    def assign_bed(self) -> None:
        piece, resident = self.page.selected_furniture, self.page.selected_resident
        if piece and resident:
            self.page.report(self.page.service.run(lambda world: world.assign_bed(piece, resident)))
            self.page.refresh()


class ShopPanel:
    """Furniture and materials as pictures with their price; bought furniture goes straight into the home."""

    def __init__(self, page: PetHomePage) -> None:
        self.page = page
        self.lifetime = page.lifetime
        section = self.section = page.add_section("pet_home_shop_section", "Shop")
        self.items = ThingGrid(rows=2)
        self.items.itemDoubleClicked.connect(lambda _item: self.buy())
        section.add_widget(self.items)
        section.add_inline(_button("pet_home_buy", "Buy", self.buy),
                           _button("pet_home_sell", "Sell one", self.sell))

    def refresh_lists(self) -> None:
        world, zone = self.page.service.world, self.page.zone
        theme = world.zones[zone].theme if world is not None and zone else "warm_home"
        things = []
        for definition in (world.catalog.furniture.values() if world else ()):
            if not definition.essential:
                name = translate(definition.label_key, definition.fallback)
                if goals.unlocked(world, definition.unlock_level):
                    text = translate("pet_home_price", "{name} — {price} coins").format(name=name, price=definition.price)
                else:
                    text = name + " — " + translate("pet_home_unlock_level", "home level {level}").format(
                        level=definition.unlock_level)
                things.append((FURNITURE_PREFIX + definition.identifier,
                               thing_icon(FURNITURE_PREFIX + definition.identifier, theme), text))
        for item in (world.catalog.items.values() if world else ()):
            if item.buy_price:
                things.append((item.identifier, thing_icon(item.identifier),
                               translate("pet_home_price", "{name} — {price} coins").format(
                                   name=translate(item.label_key, item.fallback), price=item.buy_price)))
        self.items.set_things(things)

    @owned_action
    def buy(self) -> None:
        key, zone = self.items.current_key(), self.page.zone
        if not key:
            self.page.report("pick_item")
            return
        if key.startswith(FURNITURE_PREFIX):
            definition = key.removeprefix(FURNITURE_PREFIX)
            code = self.page.service.run(lambda world: world.buy_and_place(definition, zone, "buy-" + uuid.uuid4().hex))
        else:
            code = self.page.service.run(lambda world: world.buy_item(key, 1, "buy-" + uuid.uuid4().hex))
        self.page.report(code)
        self.page.refresh()

    @owned_action
    def sell(self) -> None:
        key = self.items.current_key()
        if key and key.startswith(FURNITURE_PREFIX):
            definition = key.removeprefix(FURNITURE_PREFIX)
            self.page.report(self.page.service.run(lambda world: world.sell(definition, "sell-" + uuid.uuid4().hex)))
            self.page.refresh()


class StoragePanel:
    """The backpack: every stack the home owns as a picture, with goods that can be sold."""

    def __init__(self, page: PetHomePage) -> None:
        self.page = page
        self.lifetime = page.lifetime
        section = self.section = page.add_section("pet_home_storage_section", "Backpack")
        self.collection = QLabel()
        self.collection.setWordWrap(True)
        section.add_widget(self.collection)
        self.list = ThingGrid(rows=2)
        section.add_widget(self.list)
        section.add_inline(_button("pet_home_sell_item", "Sell one", self.sell))

    def refresh_lists(self) -> None:
        world, zone = self.page.service.world, self.page.zone
        theme = world.zones[zone].theme if world is not None and zone else "warm_home"
        if world is not None:
            owned = {piece.definition for piece in world.furniture.values()}
            owned |= {key for key in world.catalog.furniture if world.stored(key)}
            self.collection.setText(translate("pet_home_collection", "Furniture collection: {owned} of {total}")
                                    .format(owned=len(owned), total=len(world.catalog.furniture)))
        self.list.set_things([(name, thing_icon(name, theme), self._line(world, name, count))
                              for name, count in (sorted(world.ledger.items.items()) if world else ())])

    @staticmethod
    def _line(world, name: str, count: int) -> str:
        label = item_name(world, name)
        reserved = world.ledger.reserved.get(name, 0)
        text = translate("pet_home_stack", "{name} × {count}").format(name=label, count=count)
        if reserved:
            text += " " + translate("pet_home_reserved", "({count} set aside for work)").format(count=reserved)
        price = world.catalog.sell_price(name)
        if price:
            text += " — " + translate("pet_home_sells_for", "sells for {price}").format(price=price)
        return text

    @owned_action
    def sell(self) -> None:
        name = self.list.current_key()
        if name is None:
            return
        if name.startswith(FURNITURE_PREFIX):
            code = self.page.service.run(lambda world: world.sell(name.removeprefix(FURNITURE_PREFIX),
                                                                  "sell-" + uuid.uuid4().hex))
        else:
            code = self.page.service.run(lambda world: world.sell_item(name, 1, "sell-" + uuid.uuid4().hex))
        self.page.report(code)
        self.page.refresh()


item_name = item_label


def recipe_details(world, recipe) -> str:
    """Everything a job asks for and gives, shown before it is assigned."""
    def stacks(values: dict) -> str:
        return ", ".join(f"{item_name(world, name)} × {count}" for name, count in values.items()) or "—"
    return translate("pet_home_recipe_details",
                     "Takes {minutes} min · uses {inputs} · makes {outputs} · {coins} coins · "
                     "energy −{energy}/min · needs level {level}").format(
        minutes=f"{recipe.duration_ms / 60000:g}", inputs=stacks(recipe.inputs), outputs=stacks(recipe.outputs),
        coins=recipe.coins, energy=recipe.energy_per_minute, level=recipe.min_level)


class WorkPanel:
    """Jobs the residents took up by themselves, with their progress; any of them can be called off."""

    def __init__(self, page: PetHomePage) -> None:
        self.page = page
        self.lifetime = page.lifetime
        section = self.section = page.add_section("pet_home_work_section", "Work")
        self.details = tr(QLabel(), "pet_home_work_auto",
                          "Residents take up the work their workstations allow during their working hours, "
                          "using only materials already in the backpack.")
        self.details.setWordWrap(True)
        section.add_widget(self.details)
        self.empty = tr(QLabel(), "pet_home_work_empty",
                        "No jobs yet. Check residents' routines, workstations and materials in the backpack.")
        self.empty.setWordWrap(True)
        section.add_widget(self.empty)
        self.tasks = QListWidget()
        tr(self.tasks, "pet_home_work_section", "Work", "setAccessibleName")
        self.tasks.setIconSize(QSize(32, 32))
        self.tasks.setMinimumHeight(150)
        section.add_widget(self.tasks)
        self.cancel_button = _button("pet_home_cancel_task", "Cancel job", self.cancel)
        self.cancel_button.setEnabled(False)
        section.add_inline(self.cancel_button)
        self.tasks.itemSelectionChanged.connect(self._refresh_cancel)
        self.focus_check = tr(QCheckBox(), "pet_home_focus_companion",
                              "Pets work alongside my focus sessions (the pet page's focus timer)")
        self.focus_check.setChecked(user_setting_dict.get(FOCUS_KEY) is True)
        self.focus_check.toggled.connect(self._focus_toggled)
        section.add_widget(self.focus_check)

    @owned_action
    def _focus_toggled(self, checked: bool) -> None:
        user_setting_dict[FOCUS_KEY] = bool(checked)
        if not checked:
            self.page.focus_phase_changed("stopped")

    def refresh_lists(self) -> None:
        self.refresh_live()

    def refresh_live(self) -> None:
        world = self.page.service.world
        selected_items = self.tasks.selectedItems()
        selected = selected_items[0].data(ROLE_ID) if selected_items else None
        tasks = sorted(world.tasks.values(), key=lambda t: int(t.identifier[1:])) if world else []
        self.empty.setVisible(world is not None and not tasks)
        self.tasks.setVisible(bool(tasks))
        lines = [(task.identifier, task.recipe, self._task_text(world, task)) for task in tasks]
        if [self.tasks.item(row).data(ROLE_ID) for row in range(self.tasks.count())] != [i for i, _r, _t in lines]:
            self.tasks.clear()
            for identifier, recipe, text in lines:
                item = QListWidgetItem(thing_icon("recipe:" + recipe), text)
                item.setData(ROLE_ID, identifier)
                self.tasks.addItem(item)
                if identifier == selected:
                    self.tasks.setCurrentItem(item)
        else:
            for row, (_identifier, _recipe, text) in enumerate(lines):
                self.tasks.item(row).setText(text)
        self._refresh_cancel()

    def _refresh_cancel(self) -> None:
        world = self.page.service.world
        items = self.tasks.selectedItems()
        task = world.tasks.get(items[0].data(ROLE_ID)) if world is not None and items else None
        self.cancel_button.setEnabled(bool(task and task.open))

    @staticmethod
    def _task_text(world, task) -> str:
        recipe = world.catalog.recipes[task.recipe]
        resident = world.residents.get(task.resident)
        state = translate("pet_home_state_" + task.state, task.state)
        if task.progress_ms:
            phase = recipe.phase_at(task.progress_ms)
            state += " · " + translate("pet_game_phase_" + phase, phase)
        return translate("pet_home_task_line", "{resident}: {recipe} {done}/{units} — {state} {percent}%").format(
            resident=resident.name if resident else "?", recipe=translate(recipe.label_key, recipe.fallback),
            done=task.done, units=task.units, state=state,
            percent=task.progress_ms * 100 // recipe.duration_ms)

    @owned_action
    def cancel(self) -> None:
        items = self.tasks.selectedItems()
        if items:
            task = items[0].data(ROLE_ID)
            self.page.report(self.page.service.run(lambda world: world.cancel_task(task)))
            self.refresh_live()
