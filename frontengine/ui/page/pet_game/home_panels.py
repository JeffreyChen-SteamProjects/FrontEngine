"""Panels of the Pet home page: residents, furniture, shop and work.

Panels never change the world themselves; every action goes through
``HomeService.run`` so it is saved and published like any other command.
"""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QComboBox, QLabel, QListWidget, QListWidgetItem, QProgressBar, QPushButton
from PySide6.QtCore import QSize, Qt

from frontengine.show.pet_game.captions import (
    NEED_KEYS, activity_text, friends_text, item_label, traits_text, wish_text,
)
from frontengine.ui.page.pet_game.home_things import ROLE_KEY, ThingGrid, thing_icon, thing_pixmap
from frontengine.utils.multi_language.retranslate import retranslator, translate, tr
from frontengine.utils.pet_game import goals
from frontengine.utils.pet_game.catalog import FURNITURE_PREFIX
from frontengine.utils.pet_game.layout import THEMES
from frontengine.utils.pet_game.world import COMMANDS

if TYPE_CHECKING:
    from frontengine.ui.page.pet_game.home_page import PetHomePage

ROLE_ID = Qt.ItemDataRole.UserRole


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

    def command(self, command: str) -> None:
        resident = self.page.selected_resident
        if resident:
            self.page.report(self.page.service.run(lambda world: world.command(resident, command)))

    def adopt(self) -> None:
        identifier = self.profiles.currentData()
        if identifier:
            self.page.report(self.page.service.adopt(identifier))
            self.page.refresh()
            self.page.select_resident(identifier)

    def new_pet(self) -> None:
        record = self.page.profiles.create()
        self.page.report(self.page.service.adopt(record["id"]))
        self.page.refresh()
        self.page.select_resident(record["id"])

    def wardrobe(self) -> None:
        """The existing wardrobe; applying goes through the home's own lease on this pet."""
        identifier = self.page.selected_resident
        if not identifier:
            self.page.report("pick_resident")
            return
        dialog = self.wardrobes.get(identifier)
        if dialog is None:
            from frontengine.ui.dialog.pet_wardrobe import PetWardrobeDialog
            dialog = PetWardrobeDialog(self.page.profiles, identifier, self.page)
            dialog.destroyed.connect(lambda _obj=None, key=identifier: self.wardrobes.pop(key, None))
            self.wardrobes[identifier] = dialog
        dialog.show()
        dialog.raise_()

    def release(self) -> None:
        resident = self.page.selected_resident
        if resident:
            self.page.report(self.page.service.release(resident))
            self.page.select_resident(None)


class LayoutPanel:
    """Furniture: storage as pictures; placing finds a free spot, arranging places where you click."""

    def __init__(self, page: PetHomePage) -> None:
        self.page = page
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
        section.add_row("pet_home_selected_furniture", self.selected, "Selected")
        self.actions = [_button("pet_home_flip", "Mirror", self.mirror),
                        _button("pet_home_store", "Put away", self.store),
                        _button("pet_home_assign_bed", "Give bed to resident", self.assign_bed)]
        section.add_inline(*self.actions)
        self.hint.setVisible(False)
        self.preview_cell: int | None = None

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
            self.theme.setCurrentIndex(self.theme.findData(theme))
        self.place_button.setEnabled(bool(things))
        self._refresh_selected()
        self.update_preview()

    def _refresh_selected(self) -> None:
        world = self.page.service.world
        piece = world.furniture.get(self.page.selected_furniture) if world else None
        self.selected.setText(furniture_name(world, piece.definition) if piece else
                              translate("pet_home_nothing_selected", "Click a piece of furniture"))
        for button in self.actions:
            button.setEnabled(piece is not None)

    def _theme_chosen(self, _index: int) -> None:
        theme, zone = self.theme.currentData(), self.page.zone
        if theme and zone:
            self.page.report(self.page.service.run(lambda world: world.set_theme(zone, theme)))
            thing_pixmap.cache_clear()
            self.page.refresh()

    def toggle_arrange(self) -> None:
        self.arranging = not self.arranging
        retranslator.set_text(self.arrange, "pet_home_arrange_done" if self.arranging else "pet_home_arrange",
                              "Done arranging" if self.arranging else "Arrange")
        self.hint.setVisible(self.arranging)
        self.preview_cell = None
        self.page.set_arranging(self.arranging)
        self.update_preview()

    def update_preview(self, *_args) -> None:
        """While arranging, the chosen piece shows at the last clicked spot with the reason it would not fit."""
        world, zone = self.page.service.world, self.page.zone
        definition = self.storage.current_key()
        if not self.arranging or world is None or zone is None or definition is None or self.preview_cell is None:
            self.page.set_preview(None)
            return
        problem = world.preview(definition, zone, self.preview_cell)
        self.page.set_preview((definition, self.preview_cell, False, problem))

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
            self.page.report(self.page.service.run(lambda world: world.move(piece, cell, False)))
            self.page.refresh()

    def _place_at(self, definition: str, cell: int | None) -> None:
        zone = self.page.zone
        if cell is None:
            result, identifier = self.page.service.run(lambda world: world.place_anywhere(definition, zone))
        else:
            result, identifier = self.page.service.run(lambda world: world.place(definition, zone, cell))
        self.page.report(result)
        if identifier:
            self.page.selected_furniture = identifier
            self.preview_cell = None
        self.page.refresh()

    def place(self) -> None:
        """Put the chosen stored piece in the first free spot."""
        definition = self.storage.current_key() or (self.storage.item(0).data(ROLE_KEY) if self.storage.count() else None)
        if definition and self.page.zone:
            self._place_at(definition, None)

    def mirror(self) -> None:
        world, piece = self.page.service.world, self.page.selected_furniture
        found = world.furniture.get(piece) if world and piece else None
        if found is not None:
            self.page.report(self.page.service.run(lambda w: w.move(piece, found.cell, not found.flipped)))
            self.page.refresh()

    def store(self) -> None:
        piece = self.page.selected_furniture
        if piece:
            self.page.report(self.page.service.run(lambda world: world.store(piece)))
            self.page.selected_furniture = None
            self.page.refresh()

    def assign_bed(self) -> None:
        piece, resident = self.page.selected_furniture, self.page.selected_resident
        if piece and resident:
            self.page.report(self.page.service.run(lambda world: world.assign_bed(piece, resident)))
            self.page.refresh()


class ShopPanel:
    """Furniture and materials as pictures with their price; bought furniture goes straight into the home."""

    def __init__(self, page: PetHomePage) -> None:
        self.page = page
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
        section = self.section = page.add_section("pet_home_storage_section", "Backpack")
        self.collection = QLabel()
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
        section = self.section = page.add_section("pet_home_work_section", "Work")
        self.details = tr(QLabel(), "pet_home_work_auto",
                          "Residents take up the work their workstations allow during their working hours, "
                          "using only materials already in the backpack.")
        self.details.setWordWrap(True)
        section.add_widget(self.details)
        self.tasks = QListWidget()
        self.tasks.setIconSize(QSize(32, 32))
        self.tasks.setMinimumHeight(150)
        section.add_widget(self.tasks)
        section.add_inline(_button("pet_home_cancel_task", "Cancel job", self.cancel))

    def refresh_lists(self) -> None:
        self.refresh_live()

    def refresh_live(self) -> None:
        world = self.page.service.world
        selected = self.tasks.currentItem().data(ROLE_ID) if self.tasks.currentItem() else None
        tasks = sorted(world.tasks.values(), key=lambda t: int(t.identifier[1:])) if world else []
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

    def cancel(self) -> None:
        item = self.tasks.currentItem()
        if item is not None:
            task = item.data(ROLE_ID)
            self.page.report(self.page.service.run(lambda world: world.cancel_task(task)))
            self.refresh_live()
