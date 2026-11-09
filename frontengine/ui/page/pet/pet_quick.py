"""The top of the desktop pet page: put a pet on the desktop in one click, and look after the ones there.

Every built-in character is a card; clicking one installs it if needed and puts a pet dressed
as it on the desktop at once. Below, the pets on the desktop are listed with what people do most: open the
wardrobe, bring a pet back into view, or put it away. Everything else on the page is folded away.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QIcon, QImage, QPixmap
from PySide6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QPushButton, QSizePolicy, QToolButton

from frontengine.show.pet.inkside.library import builtin_names
from frontengine.show.pet.pet_profile_session import PetProfileSession
from frontengine.utils.multi_language.retranslate import tr, translate

ICONS = Path(__file__).resolve().parents[3] / "show" / "pet" / "inkside" / "icons"
CARD_ICON = 56
CARD_COLUMNS = 3                 # six cards in two rows: fits even a narrow window
REFRESH_MS = 1000


def card_icon(identifier: str) -> QIcon:
    """The character's first sitting frame, rendered from its layered rig by tools/inkside_icons.py."""
    frame = QImage(str(ICONS / f"{identifier}.png"))
    if frame.isNull():
        return QIcon()
    return QIcon(QPixmap.fromImage(frame.scaled(CARD_ICON, CARD_ICON, Qt.AspectRatioMode.KeepAspectRatio,
                                                Qt.TransformationMode.SmoothTransformation)))


class PetQuickStart:
    """Builds the first section of the page and keeps its list of pets on the desktop current."""

    def __init__(self, page) -> None:
        self.page = page
        section = page.add_section("pet_quick_title", "Your pet")
        hint = tr(QLabel(), "pet_quick_hint", "Click a character to put it on your desktop.")
        hint.setWordWrap(True)
        section.add_widget(hint)
        self.cards: dict[str, QToolButton] = {}
        for identifier, name in builtin_names():
            card = self._card(name, card_icon(identifier))
            card.clicked.connect(lambda _checked=False, i=identifier: page.quick_builtin(i))
            self.cards[identifier] = card
        section.add_button_grid(*self.cards.values(), columns=CARD_COLUMNS)
        self.pets = QListWidget()
        self.pets.setMaximumHeight(110)
        tr(self.pets, "pet_quick_on_desktop", "Your pets on the desktop", "setAccessibleName")
        self.pets.itemDoubleClicked.connect(lambda _item: self.bring_back())
        self.empty = tr(QLabel(), "pet_quick_none", "No pet on the desktop yet.")
        self.empty.setWordWrap(True)
        section.add_widget(self.pets, "pet_quick_on_desktop", "Your pets on the desktop")
        section.add_widget(self.empty)
        self.wardrobe_button = self._button("pet_wardrobe_title", "Wardrobe", self.wardrobe)
        self.back_button = self._button("pet_recover", "Bring pet back", self.bring_back)
        self.away_button = self._button("pet_quick_put_away", "Put away", self.put_away)
        section.add_inline(self.wardrobe_button, self.back_button, self.away_button)
        self.timer = QTimer(self.pets)           # pets close themselves from their own menus too
        self.timer.timeout.connect(self.refresh)
        self.timer.start(REFRESH_MS)
        self.refresh()

    @staticmethod
    def _card(text: str, icon: QIcon) -> QToolButton:
        card = QToolButton()
        card.setText(text)
        card.setIcon(icon)
        card.setIconSize(QSize(CARD_ICON, CARD_ICON))
        card.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        card.setMinimumWidth(CARD_ICON + 12)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        return card

    @staticmethod
    def _button(key: str, fallback: str, slot) -> QPushButton:
        button = tr(QPushButton(), key, fallback)
        button.clicked.connect(slot)
        return button

    def live_pets(self) -> list:
        pets = []
        for pet in list(self.page.pet_list):
            try:
                session = pet.profile_session
                if not session._closed:
                    pets.append(pet)
            except RuntimeError:          # already deleted
                continue
        return pets

    def refresh(self) -> None:
        pets = self.live_pets()
        wanted = [(pet.profile_session.identifier, pet.profile_session.state()["name"]) for pet in pets]
        current = [(self.pets.item(i).data(Qt.ItemDataRole.UserRole), self.pets.item(i).text())
                   for i in range(self.pets.count())]
        if wanted != current:
            selected = self.selected()
            self.pets.clear()
            for identifier, name in wanted:
                item = QListWidgetItem(name)
                item.setData(Qt.ItemDataRole.UserRole, identifier)
                self.pets.addItem(item)
                if identifier == selected:
                    self.pets.setCurrentItem(item)
            if self.pets.currentItem() is None and self.pets.count():
                self.pets.setCurrentRow(self.pets.count() - 1)
        has = bool(wanted)
        self.pets.setVisible(has)
        self.empty.setVisible(not has)
        for button in (self.wardrobe_button, self.back_button, self.away_button):
            button.setEnabled(has)

    def selected(self) -> str | None:
        item = self.pets.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else None

    def _pet(self):
        identifier = self.selected()
        session = PetProfileSession.active(self.page.profile_controls.profiles, identifier) if identifier else None
        return session.parent() if session is not None else None

    def wardrobe(self) -> None:
        if self.selected():
            self.page.profile_controls.wardrobe(self.selected())

    def bring_back(self) -> None:
        from frontengine.show.pet.recovery import recover_pet
        pet = self._pet()
        if pet is None:
            return
        target = self.page._target_geometry()
        try:
            recover_pet(pet, target[1] if target else pet.screen())
        except (ValueError, RuntimeError):
            self.page.profile_controls.status.setText(translate(
                "pet_recover_failed", "Could not bring the pet back. Check the screen and reduce the pet size if needed."))

    def put_away(self) -> None:
        pet = self._pet()
        if pet is not None and pet.close():
            if pet in self.page.pet_list:          # closed is gone: the page stops tracking it
                self.page.pet_list.remove(pet)
            self.refresh()
