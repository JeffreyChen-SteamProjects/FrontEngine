"""The Goals section: home level, tutorial, today's commissions, the celebration and life events."""
from __future__ import annotations

from datetime import datetime
from os import getcwd
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QPushButton

from frontengine.show.pet_game.captions import item_label
from frontengine.utils.multi_language.retranslate import translate, tr
from frontengine.utils.pet_game import goals
from frontengine.utils.pet_game.schedule import game_day

if TYPE_CHECKING:
    from frontengine.ui.page.pet_game.home_page import PetHomePage

ROLE_ID = Qt.ItemDataRole.UserRole
ALBUM_FOLDER = "pet-album"
EVENTS_SHOWN = 5


def _button(key: str, fallback: str, callback) -> QPushButton:
    button = tr(QPushButton(), key, fallback)
    button.clicked.connect(callback)
    return button


class GoalsPanel:
    def __init__(self, page: PetHomePage) -> None:
        self.page = page
        section = self.section = page.add_section("pet_home_goals_section", "Goals")
        self.level = QLabel()
        section.add_widget(self.level)
        self.tutorial = QListWidget()
        self.tutorial.setMaximumHeight(160)
        section.add_widget(self.tutorial, "pet_home_tutorial", "Getting started")
        section.add_inline(_button("pet_home_skip_tutorial", "Skip the tutorial", self.skip))
        self.commissions = QListWidget()
        self.commissions.setMaximumHeight(90)
        section.add_widget(self.commissions, "pet_home_commissions", "Today's commissions")
        auto = tr(QLabel(), "pet_home_goals_auto",
                  "Rewards are collected and commissions handed in by themselves once they are ready.")
        auto.setWordWrap(True)
        section.add_widget(auto)
        self.celebrate_button = _button("pet_home_celebrate", "Hold a home celebration", self.celebrate)
        self.events = QLabel()
        self.events.setWordWrap(True)
        section.add_widget(self.events, "pet_home_life_events", "Recent moments")
        section.add_inline(self.celebrate_button, _button("pet_home_photo", "Take a photo", self.take_photo))

    def refresh_lists(self) -> None:
        world = self.page.service.world
        if world is None:
            return
        goals.refresh_commissions(world)
        self.level.setText(translate("pet_home_level", "Home level {level}").format(level=goals.home_level(world)))
        self._fill(self.tutorial, [(goal.identifier, self._goal_line(world, goal)) for goal in goals.TUTORIAL])
        offers = world.progress.commissions["offers"]
        self._fill(self.commissions, [(str(index), self._offer_line(world, offer))
                                      for index, offer in enumerate(offers)])
        self.celebrate_button.setEnabled(goals.celebration_ready(world))
        recent = world.progress.events[-EVENTS_SHOWN:][::-1]
        self.events.setText("\n".join(self._event_line(world, event) for event in recent)
                            or translate("pet_home_no_events", "Nothing yet; moments appear as your pets live."))

    @staticmethod
    def _fill(widget: QListWidget, rows: list[tuple[str, str]]) -> None:
        selected = widget.currentItem().data(ROLE_ID) if widget.currentItem() else None
        widget.clear()
        for identifier, text in rows:
            item = QListWidgetItem(text)
            item.setData(ROLE_ID, identifier)
            widget.addItem(item)
            if identifier == selected:
                widget.setCurrentItem(item)

    @staticmethod
    def _goal_line(world, goal) -> str:
        state = goals.goal_state(world, goal)
        current, target = goal.measure(world)
        mark = {"claimed": "✔", "done": "★", "skipped": "–", "open": "○"}[state]
        name = translate("pet_game_goal_" + goal.identifier, goal.identifier)
        return translate("pet_home_goal_line", "{mark} {name} ({current}/{target}) · {coins} coins").format(
            mark=mark, name=name, current=min(current, target), target=target, coins=goal.coins)

    @staticmethod
    def _offer_line(world, offer: dict) -> str:
        status = "✔ " if offer["done"] else ""
        return status + translate("pet_home_offer_line", "{count} × {item} → {coins} coins").format(
            count=offer["count"], item=item_label(world, offer["item"]), coins=offer["coins"])

    @staticmethod
    def _event_line(world, event: dict) -> str:
        resident = world.residents.get(event["resident"]) if event["resident"] else None
        text = translate("pet_game_event_" + event["kind"], event["kind"])
        name = resident.name if resident else ""
        return translate("pet_home_event_line", "Day {day}: {text} {name}").format(
            day=event["day"], text=text, name=name).strip()

    def claim(self) -> None:
        item = self.tutorial.currentItem()
        if item is not None:
            self.page.report(self.page.service.run(lambda world: goals.claim(world, item.data(ROLE_ID))))
            self.page.refresh()

    def skip(self) -> None:
        self.page.report(self.page.service.run(goals.skip_tutorial))
        self.page.refresh()

    def deliver(self) -> None:
        item = self.commissions.currentItem()
        if item is not None:
            index = int(item.data(ROLE_ID))
            self.page.report(self.page.service.run(lambda world: goals.deliver(world, index)))
            self.page.refresh()

    def celebrate(self) -> None:
        self.page.report(self.page.service.run(goals.celebrate))
        self.page.refresh()

    def take_photo(self) -> Path | None:
        """Only the home drawing is saved; nothing on the desktop is captured."""
        world = self.page.service.world
        if world is None:
            return None
        folder = Path(getcwd()) / ALBUM_FOLDER
        folder.mkdir(exist_ok=True)
        target = folder / f"day{game_day(world.time_ms)}-{datetime.now():%Y%m%d-%H%M%S}.png"
        if not self.page.view.grab().save(str(target), "PNG"):
            self.page.report_text(translate("pet_home_photo_failed", "The photo could not be saved."))
            return None
        self.page.report_text(translate("pet_home_photo_saved", "Photo saved to {path}").format(path=target))
        return target
