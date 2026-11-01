"""Panels of the Pet home page: residents, furniture, shop and work.

Panels never change the world themselves; every action goes through
``HomeService.run`` so it is saved and published like any other command.
"""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QLabel, QListWidget, QListWidgetItem, QProgressBar, QPushButton, QSpinBox,
)
from PySide6.QtCore import Qt

from frontengine.show.pet_game.captions import (
    NEED_KEYS, activity_text, friends_text, item_label, traits_text, wish_text,
)
from frontengine.utils.multi_language.retranslate import retranslator, translate, tr
from frontengine.utils.pet_game.catalog import FURNITURE_PREFIX
from frontengine.utils.pet_game.schedule import TEMPLATES
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
        self.routine = QComboBox()
        self.routine.activated.connect(self._routine_chosen)
        section.add_row("pet_home_routine", self.routine, "Routine")
        self.commands = [_button("pet_home_cmd_" + command, command.title(),
                                 lambda _checked=False, c=command: self.command(c)) for command in COMMANDS]
        section.add_inline(*self.commands)
        section.add_inline(_button("pet_home_release", "Move out", self.release))

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
        self.routine.clear()
        for routine in TEMPLATES:
            self.routine.addItem(translate("pet_home_routine_" + routine, routine), routine)

    def refresh_live(self) -> None:
        world = self.page.service.world
        resident = world.residents.get(self.page.selected_resident) if world else None
        for control in (*self.bars.values(), self.routine, *self.commands):
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
        index = self.routine.findData(resident.routine)
        if index != self.routine.currentIndex():
            self.routine.setCurrentIndex(index)

    def _list_changed(self, current, _previous) -> None:
        if current is not None:
            self.page.select_resident(current.data(ROLE_ID))

    def _routine_chosen(self, _index: int) -> None:
        resident = self.page.selected_resident
        if resident:
            self.page.report(self.page.service.run(lambda world: world.set_routine(resident, self.routine.currentData())))

    def command(self, command: str) -> None:
        resident = self.page.selected_resident
        if resident:
            self.page.report(self.page.service.run(lambda world: world.command(resident, command)))

    def adopt(self) -> None:
        identifier = self.profiles.currentData()
        if identifier:
            self.page.report(self.page.service.adopt(identifier))
            self.page.select_resident(identifier)

    def new_pet(self) -> None:
        record = self.page.profiles.create()
        self.page.report(self.page.service.adopt(record["id"]))
        self.page.select_resident(record["id"])

    def release(self) -> None:
        resident = self.page.selected_resident
        if resident:
            self.page.report(self.page.service.release(resident))
            self.page.select_resident(None)


class LayoutPanel:
    """Arranging furniture: choose from storage, preview with reasons, place, move, put away."""

    def __init__(self, page: PetHomePage) -> None:
        self.page = page
        self.arranging = False
        section = self.section = page.add_section("pet_home_layout_section", "Furniture")
        self.arrange = _button("pet_home_arrange", "Arrange", self.toggle_arrange)
        self.hint = tr(QLabel(), "pet_home_arrange_hint",
                       "Click the floor to choose a position. Esc stops arranging.")
        self.hint.setWordWrap(True)
        section.add_inline(self.arrange)
        section.add_widget(self.hint)
        self.storage = QComboBox()
        self.storage.currentIndexChanged.connect(self.update_preview)
        section.add_row("pet_home_storage", self.storage, "In storage")
        self.cell = QSpinBox()
        self.cell.valueChanged.connect(self.update_preview)
        section.add_row("pet_home_cell", self.cell, "Position")
        self.flip = tr(QCheckBox(), "pet_home_flip", "Mirror")
        self.flip.toggled.connect(self.update_preview)
        section.add_widget(self.flip)
        self.selected = QLabel()
        section.add_row("pet_home_selected_furniture", self.selected, "Selected")
        self.actions = [_button("pet_home_place", "Place", self.place),
                        _button("pet_home_move_here", "Move to position", self.move),
                        _button("pet_home_store", "Put away", self.store),
                        _button("pet_home_assign_bed", "Give bed to resident", self.assign_bed)]
        section.add_inline(*self.actions)
        self.hint.setVisible(False)

    def refresh_lists(self) -> None:
        world = self.page.service.world
        current = self.storage.currentData()
        self.storage.blockSignals(True)
        self.storage.clear()
        if world is not None:
            for definition in world.catalog.furniture:
                count = world.stored(definition)
                if world.sandbox or count:
                    label = furniture_name(world, definition)
                    if not world.sandbox:
                        label = translate("pet_home_stack", "{name} × {count}").format(name=label, count=count)
                    self.storage.addItem(label, definition)
            zone = self.page.zone
            self.cell.setRange(0, world.zones[zone].width_cells - 1 if zone else 0)
        index = self.storage.findData(current)
        self.storage.setCurrentIndex(max(0, index))
        self.storage.blockSignals(False)
        self._refresh_selected()
        self.update_preview()

    def _refresh_selected(self) -> None:
        world = self.page.service.world
        piece = world.furniture.get(self.page.selected_furniture) if world else None
        self.selected.setText(furniture_name(world, piece.definition) if piece else
                              translate("pet_home_nothing_selected", "Click a piece of furniture"))
        for button in self.actions[1:]:
            button.setEnabled(piece is not None)

    def toggle_arrange(self) -> None:
        self.arranging = not self.arranging
        retranslator.set_text(self.arrange, "pet_home_arrange_done" if self.arranging else "pet_home_arrange",
                              "Done arranging" if self.arranging else "Arrange")
        self.hint.setVisible(self.arranging)
        self.page.set_arranging(self.arranging)
        self.update_preview()

    def update_preview(self, *_args) -> None:
        world, zone = self.page.service.world, self.page.zone
        definition = self.storage.currentData()
        if not self.arranging or world is None or zone is None or definition is None:
            self.page.set_preview(None)
            return
        problem = world.preview(definition, zone, self.cell.value())
        self.page.set_preview((definition, self.cell.value(), self.flip.isChecked(), problem))

    def cell_clicked(self, cell: int) -> None:
        if self.arranging:
            self.cell.setValue(cell)

    def place(self) -> None:
        definition = self.storage.currentData()
        if definition and self.page.zone:
            result, identifier = self.page.service.run(
                lambda world: world.place(definition, self.page.zone, self.cell.value(), self.flip.isChecked()))
            self.page.report(result)
            if identifier:
                self.page.selected_furniture = identifier
            self.page.refresh()

    def move(self) -> None:
        piece = self.page.selected_furniture
        if piece:
            self.page.report(self.page.service.run(
                lambda world: world.move(piece, self.cell.value(), self.flip.isChecked())))
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
    """Furniture and materials to buy; selling furniture back returns its listed amount."""

    def __init__(self, page: PetHomePage) -> None:
        self.page = page
        section = self.section = page.add_section("pet_home_shop_section", "Shop")
        self.items = QComboBox()
        section.add_row("pet_home_shop_item", self.items, "Item")
        section.add_inline(_button("pet_home_buy", "Buy", self.buy),
                           _button("pet_home_sell", "Sell one from storage", self.sell))
        self.materials = QComboBox()
        section.add_row("pet_home_materials", self.materials, "Materials")
        self.amount = QSpinBox()
        self.amount.setRange(1, 99)
        section.add_row("pet_home_amount", self.amount, "Amount")
        section.add_inline(_button("pet_home_buy_materials", "Buy materials", self.buy_materials))

    def refresh_lists(self) -> None:
        world = self.page.service.world
        current, material = self.items.currentData(), self.materials.currentData()
        self.items.clear()
        self.materials.clear()
        for definition in (world.catalog.furniture.values() if world else ()):
            if not definition.essential:
                label = translate("pet_home_price", "{name} — {price} coins").format(
                    name=translate(definition.label_key, definition.fallback), price=definition.price)
                self.items.addItem(label, definition.identifier)
        for item in (world.catalog.items.values() if world else ()):
            if item.buy_price:
                self.materials.addItem(translate("pet_home_price", "{name} — {price} coins").format(
                    name=translate(item.label_key, item.fallback), price=item.buy_price), item.identifier)
        self.items.setCurrentIndex(max(0, self.items.findData(current)))
        self.materials.setCurrentIndex(max(0, self.materials.findData(material)))

    def buy(self) -> None:
        definition = self.items.currentData()
        if definition:
            self.page.report(self.page.service.run(lambda world: world.buy(definition, "buy-" + uuid.uuid4().hex)))
            self.page.refresh()

    def sell(self) -> None:
        definition = self.items.currentData()
        if definition:
            self.page.report(self.page.service.run(lambda world: world.sell(definition, "sell-" + uuid.uuid4().hex)))
            self.page.refresh()

    def buy_materials(self) -> None:
        name, count = self.materials.currentData(), self.amount.value()
        if name:
            self.page.report(self.page.service.run(
                lambda world: world.buy_item(name, count, "buy-" + uuid.uuid4().hex)))
            self.page.refresh()


class StoragePanel:
    """The backpack: every stack the home owns, with goods that can be sold."""

    def __init__(self, page: PetHomePage) -> None:
        self.page = page
        section = self.section = page.add_section("pet_home_storage_section", "Backpack")
        self.collection = QLabel()
        section.add_widget(self.collection)
        self.list = QListWidget()
        self.list.setMaximumHeight(140)
        section.add_widget(self.list)
        section.add_inline(_button("pet_home_sell_item", "Sell one", self.sell))

    def refresh_lists(self) -> None:
        world = self.page.service.world
        selected = self.list.currentItem().data(ROLE_ID) if self.list.currentItem() else None
        self.list.clear()
        if world is not None:
            owned = {piece.definition for piece in world.furniture.values()}
            owned |= {key for key in world.catalog.furniture if world.stored(key)}
            self.collection.setText(translate("pet_home_collection", "Furniture collection: {owned} of {total}")
                                    .format(owned=len(owned), total=len(world.catalog.furniture)))
        for name, count in sorted(world.ledger.items.items()) if world else ():
            item = QListWidgetItem(self._line(world, name, count))
            item.setData(ROLE_ID, name)
            self.list.addItem(item)
            if name == selected:
                self.list.setCurrentItem(item)

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
        item = self.list.currentItem()
        if item is None:
            return
        name = item.data(ROLE_ID)
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
    def __init__(self, page: PetHomePage) -> None:
        self.page = page
        section = self.section = page.add_section("pet_home_work_section", "Work")
        self.recipes = QComboBox()
        self.recipes.currentIndexChanged.connect(self._recipe_changed)
        section.add_row("pet_home_recipe", self.recipes, "Job")
        self.details = QLabel()
        self.details.setWordWrap(True)
        section.add_widget(self.details)
        self.station = QComboBox()
        section.add_row("pet_home_station", self.station, "Workstation")
        self.units = QSpinBox()
        self.units.setRange(1, 20)
        section.add_row("pet_home_units", self.units, "How many")
        self.priority = QSpinBox()
        self.priority.setRange(0, 9)
        self.priority.setValue(5)
        section.add_row("pet_home_priority", self.priority, "Priority")
        section.add_inline(_button("pet_home_assign_work", "Give to resident", self.assign))
        self.tasks = QListWidget()
        self.tasks.setMaximumHeight(120)
        section.add_widget(self.tasks)
        section.add_inline(_button("pet_home_cancel_task", "Cancel job", self.cancel))

    def refresh_lists(self) -> None:
        world = self.page.service.world
        current = self.recipes.currentData()
        self.recipes.blockSignals(True)
        self.recipes.clear()
        for recipe in (world.catalog.recipes.values() if world else ()):
            label = translate("pet_home_recipe_line", "{name} — {minutes} min, {coins} coins").format(
                name=translate(recipe.label_key, recipe.fallback), minutes=recipe.duration_ms // 60000,
                coins=recipe.coins)
            self.recipes.addItem(label, recipe.identifier)
        self.recipes.setCurrentIndex(max(0, self.recipes.findData(current)))
        self.recipes.blockSignals(False)
        self._recipe_changed()
        self.refresh_live()

    def _recipe_changed(self, *_args) -> None:
        world = self.page.service.world
        recipe = world.catalog.recipes.get(self.recipes.currentData()) if world else None
        self.details.setText(recipe_details(world, recipe) if recipe else "")
        current = self.station.currentData()
        self.station.clear()
        self.station.addItem(translate("pet_home_any_station", "Any free workstation"), None)
        for piece, definition in (world.in_zone(self.page.zone) if recipe and self.page.zone else ()):
            if definition.profession == recipe.profession:
                self.station.addItem(f"{translate(definition.label_key, definition.fallback)} ({piece.cell})",
                                     piece.identifier)
        self.station.setCurrentIndex(max(0, self.station.findData(current)))

    def refresh_live(self) -> None:
        world = self.page.service.world
        selected = self.tasks.currentItem().data(ROLE_ID) if self.tasks.currentItem() else None
        tasks = sorted(world.tasks.values(), key=lambda t: int(t.identifier[1:])) if world else []
        lines = [(task.identifier, self._task_text(world, task)) for task in tasks]
        if [self.tasks.item(row).data(ROLE_ID) for row in range(self.tasks.count())] != [i for i, _t in lines]:
            self.tasks.clear()
            for identifier, text in lines:
                item = QListWidgetItem(text)
                item.setData(ROLE_ID, identifier)
                self.tasks.addItem(item)
                if identifier == selected:
                    self.tasks.setCurrentItem(item)
        else:
            for row, (_identifier, text) in enumerate(lines):
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

    def assign(self) -> None:
        recipe, resident = self.recipes.currentData(), self.page.selected_resident
        if not resident:
            self.page.report("pick_resident")
            return
        if recipe:
            station, units, priority = self.station.currentData(), self.units.value(), self.priority.value()
            result, _task = self.page.service.run(
                lambda world: world.create_task(recipe, resident, units, station, priority))
            self.page.report(result)
            self.refresh_live()

    def cancel(self) -> None:
        item = self.tasks.currentItem()
        if item is not None:
            task = item.data(ROLE_ID)
            self.page.report(self.page.service.run(lambda world: world.cancel_task(task)))
            self.refresh_live()
