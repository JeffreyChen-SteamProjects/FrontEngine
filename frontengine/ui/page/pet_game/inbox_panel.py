"""The Inbox: what happened while you were busy, collected quietly, never a pop-up.

Events are sorted into four categories the player can switch off one by one.
Repeats of the same thing by the same pet within a minute of game time fold
into one line with a count, so a pet writing letters all afternoon is one line,
not twenty. Meals and naps a pet takes on its own are never listed.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QCheckBox, QLabel, QListWidget, QPushButton

from frontengine.show.pet_game.captions import result_text
from frontengine.user_setting.user_setting_file import user_setting_dict
from frontengine.utils.multi_language.retranslate import translate, tr

if TYPE_CHECKING:
    from frontengine.ui.page.pet_game.home_page import PetHomePage

CATEGORIES = ("work", "needs", "life", "errors")
MAX_LINES = 50
FOLD_MS = 60000


def category(event: dict) -> str | None:
    kind = event.get("kind")
    if kind in ("settled", "commission_done"):
        return "work"
    if kind == "interrupted" and event.get("reason") in ("tired", "hungry"):
        return "needs"
    if kind in ("life_event", "wish_granted"):
        return "life"
    if kind in ("settle_failed", "save_failed"):
        return "errors"
    return None


def line(world, event: dict) -> str:
    resident = world.residents.get(event.get("resident")) if world is not None else None
    name = resident.name if resident else ""
    kind = event["kind"]
    if kind == "settled":
        recipe = world.catalog.recipes.get(event.get("recipe"))
        label = translate(recipe.label_key, recipe.fallback) if recipe else event.get("recipe", "")
        return translate("pet_home_note_settled", "{name} finished {recipe} (+{coins})").format(
            name=name, recipe=label, coins=event.get("coins", 0))
    if kind == "commission_done":
        return translate("pet_home_note_commission", "Commission delivered (+{coins})").format(coins=event["coins"])
    if kind == "interrupted":
        return translate("pet_home_note_" + event["reason"], event["reason"]).format(name=name)
    if kind == "life_event":
        return (translate("pet_game_event_" + event["event"], event["event"]) + " " + name).strip()
    if kind == "wish_granted":
        return translate("pet_home_note_wish", "{name}'s wish came true").format(name=name)
    if kind == "settle_failed":
        return result_text(event.get("reason", "unknown"))
    return translate("pet_home_note_failed", "{text}").format(text=event.get("text", ""))


class InboxPanel:
    def __init__(self, page: PetHomePage) -> None:
        self.page = page
        self.entries: list[dict] = []
        self.unread = 0
        section = self.section = page.add_section("pet_home_inbox_section", "Inbox")
        self.count = QLabel()
        section.add_widget(self.count)
        self.list = QListWidget()
        self.list.setMaximumHeight(140)
        section.add_widget(self.list)
        self.filters = {}
        for name in CATEGORIES:
            box = tr(QCheckBox(), "pet_home_notify_" + name, name)
            box.setChecked(user_setting_dict.get("pet_home_notify_" + name, True) is not False)
            box.toggled.connect(lambda checked, n=name: user_setting_dict.__setitem__("pet_home_notify_" + n, checked))
            self.filters[name] = box
        section.add_inline(*self.filters.values())
        done = tr(QPushButton(), "pet_home_inbox_read", "Mark all as read")
        done.clicked.connect(self.mark_read)
        section.add_inline(done)
        self.refresh_lists()

    def wanted(self, name: str) -> bool:
        return self.filters[name].isChecked()

    def on_events(self, events: list, world) -> None:
        for event in events:
            name = category(event)
            if name is not None and self.wanted(name):
                self._add(event, name, line(world, event))
        self.refresh_lists()

    def add_error(self, text: str, time_ms: int) -> None:
        if self.wanted("errors"):
            self._add({"kind": "save_failed", "time": time_ms, "text": text}, "errors", text)
            self.refresh_lists()

    def _add(self, event: dict, name: str, text: str) -> None:
        key = (event["kind"], event.get("resident"), event.get("recipe"), event.get("reason"))
        last = self.entries[-1] if self.entries else None
        if last is not None and last["key"] == key and event.get("time", 0) - last["time"] <= FOLD_MS:
            last.update(count=last["count"] + 1, time=event.get("time", 0))
        else:
            self.entries.append({"key": key, "text": text, "count": 1, "time": event.get("time", 0),
                                 "category": name})
            self.entries = self.entries[-MAX_LINES:]
        self.unread += 1

    def mark_read(self) -> None:
        self.unread = 0
        self.refresh_lists()

    def refresh_lists(self) -> None:
        self.list.clear()
        for entry in reversed(self.entries):
            suffix = " " + translate("pet_home_note_times", "×{count}").format(count=entry["count"]) \
                if entry["count"] > 1 else ""
            self.list.addItem(entry["text"] + suffix)
        self.count.setText(translate("pet_home_inbox_unread", "{count} new").format(count=self.unread))
