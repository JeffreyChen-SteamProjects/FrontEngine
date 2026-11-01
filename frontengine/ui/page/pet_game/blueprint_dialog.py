"""Visiting a home from a blueprint file: look around, nothing runs, nothing is saved or sent."""
from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QLabel, QVBoxLayout, QWidget

from frontengine.show.pet_game.home_view import HomeView
from frontengine.ui.dialog.dialog_kit import roomy
from frontengine.utils.multi_language.retranslate import translate


class BlueprintVisit(QDialog):
    """A read-only look at someone's home; it only ever reads the file it was given."""

    def __init__(self, world, missing: dict[str, int], name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.world = world
        self.setWindowTitle(translate("pet_home_visit_title", "Visiting {name}").format(name=name))
        layout = roomy(QVBoxLayout(self))
        note = QLabel(translate("pet_home_visit_note",
                                "A look at a shared home - nothing here runs, is bought or is saved."))
        note.setWordWrap(True)
        layout.addWidget(note)
        self.zones = QComboBox()
        for index, key in enumerate(world.zones):
            self.zones.addItem(translate("pet_home_visit_zone", "Room {number}").format(number=index + 1), key)
        self.zones.currentIndexChanged.connect(self._show_zone)
        self.zones.setVisible(len(world.zones) > 1)
        layout.addWidget(self.zones)
        self.view = HomeView()
        self.view.reduced_motion = True
        self.view.drag_enabled = False
        layout.addWidget(self.view)
        self.missing = QLabel(missing_text(world, missing))
        self.missing.setWordWrap(True)
        self.missing.setVisible(bool(missing))
        layout.addWidget(self.missing)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.resize(900, 360)
        self._show_zone()

    def _show_zone(self, *_args) -> None:
        self.view.set_world(self.world, self.zones.currentData() or next(iter(self.world.zones)))


def missing_text(world, missing: dict[str, int]) -> str:
    """What could not be shown, by name when this FrontEngine knows the piece, else by its id."""
    if not missing:
        return ""
    names = []
    for key, count in sorted(missing.items()):
        found = world.catalog.furniture.get(key)
        label = translate(found.label_key, found.fallback) if found is not None else key
        names.append(f"{label} × {count}")
    return translate("pet_home_visit_missing", "Not shown here (missing content or no room): {items}").format(
        items=", ".join(names))
