"""The Inbox: what happened while you were busy, collected quietly, never a pop-up.

Events are sorted into four categories the player can switch off one by one.
Repeats of the same thing by the same pet within a minute of game time fold
into one line with a count, so a pet writing letters all afternoon is one line,
not twenty. Meals and naps a pet takes on its own are never listed.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from frontengine.ui.page.wrapping_buttons import WrappingPushButton as QPushButton

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QLabel, QListWidget

from frontengine.show.pet_game.captions import result_text
from frontengine.utils.multi_language.retranslate import translate, tr

if TYPE_CHECKING:
    from frontengine.ui.page.pet_game.home_page import PetHomePage

CATEGORIES = ("work", "needs", "life", "errors")
MAX_LINES = 50
FOLD_MS = 60000


def category(event: dict) -> str | None:
    kind = event.get("kind")
    if kind in ("settled", "commission_done", "auto_job", "goal_claimed"):
        return "work"
    if kind == "interrupted" and event.get("reason") in ("tired", "hungry"):
        return "needs"
    if kind in ("life_event", "wish_granted"):
        return "life"
    if kind in ("settle_failed", "save_failed"):
        return "errors"
    return None


def line(event: dict) -> str:
    kind = event["kind"]
    name = event.get("resident_name", "")
    if kind == "settled":
        label = translate(*event["recipe_label"])
        if not event.get("coins", 0):
            return translate("pet_home_note_settled_no_coins", "{name} finished {recipe}").format(
                name=name, recipe=label)
        return translate("pet_home_note_settled", "{name} finished {recipe} (+{coins})").format(
            name=name, recipe=label, coins=event.get("coins", 0))
    if kind == "commission_done":
        if not event["coins"]:
            return translate("pet_home_note_commission_no_coins", "Commission delivered")
        return translate("pet_home_note_commission", "Commission delivered (+{coins})").format(coins=event["coins"])
    if kind == "auto_job":
        label = translate(*event["recipe_label"])
        return translate("pet_home_note_auto_job", "{name} took up {recipe}").format(name=name, recipe=label)
    if kind == "goal_claimed":
        if not event["coins"]:
            return translate("pet_home_note_goal_completed", "Goal completed")
        return translate("pet_home_note_goal_claimed", "Reward collected (+{coins})").format(coins=event["coins"])
    if kind == "interrupted":
        return translate("pet_home_note_" + event["reason"], event["reason"]).format(name=name)
    if kind == "life_event":
        return (translate("pet_game_event_" + event["event"], event["event"]) + " " + name).strip()
    if kind == "wish_granted":
        return translate("pet_home_note_wish", "{name}'s wish came true").format(name=name)
    if kind == "settle_failed":
        return result_text(event.get("reason", "unknown"))
    return translate("pet_home_note_failed", "{text}").format(text=event.get("text", ""))


@dataclass
class _InboxHistory:
    home: str | None
    entries: list[dict] = field(default_factory=list)
    unread: int = 0


def _named(event: dict, world) -> dict:
    """The event with the names it shows: the resident's and the recipe's, as they are now."""
    message = dict(event)
    resident = world.residents.get(event.get("resident")) if world is not None else None
    recipe = world.catalog.recipes.get(event.get("recipe")) if world is not None else None
    message["resident_name"] = resident.name if resident else ""
    message["recipe_label"] = (recipe.label_key, recipe.fallback) if recipe else ("", event.get("recipe", ""))
    return message


class InboxPanel:
    def __init__(self, page: PetHomePage) -> None:
        self.page = page
        self._histories: dict[str, _InboxHistory] = {}
        section = self.section = page.add_section("pet_home_inbox_section", "Inbox")
        self.count = QLabel()
        section.add_widget(self.count)
        self.list = QListWidget()
        self.list.setMaximumHeight(140)
        section.add_widget(self.list)
        done = tr(QPushButton(), "pet_home_inbox_read", "Mark all as read")
        done.clicked.connect(self.mark_read)
        section.add_inline(done)

    @property
    def _history(self) -> _InboxHistory:
        service = self.page.service
        home = service.world.home if service.world is not None else None
        history = self._histories.get(service.mode)
        if history is None or history.home != home:
            history = self._histories[service.mode] = _InboxHistory(home)
        return history

    @property
    def entries(self) -> list[dict]:
        return self._history.entries

    @property
    def unread(self) -> int:
        return self._history.unread

    @staticmethod
    def wanted(name: str) -> bool:
        return name in CATEGORIES

    def on_events(self, events: list, world) -> None:
        for event in events:
            name = category(event)
            if name is not None and self.wanted(name):
                self._add(_named(event, world), name)
        self.refresh_lists()

    def add_error(self, text: str, time_ms: int) -> None:
        if self.wanted("errors"):
            self._add({"kind": "save_failed", "time": time_ms, "text": text}, "errors")
            self.refresh_lists()

    def _add(self, event: dict, name: str) -> None:
        history = self._history
        key = (event["kind"], event.get("resident"), event.get("recipe"), event.get("reason"),
               event.get("event"), event.get("coins"), event.get("text"), event.get("resident_name"),
               event.get("recipe_label"))
        last = history.entries[-1] if history.entries else None
        if last is not None and last["key"] == key and 0 <= event.get("time", 0) - last["time"] <= FOLD_MS:
            last.update(count=last["count"] + 1, time=event.get("time", 0))
        else:
            history.entries.append({"key": key, "event": event, "count": 1, "time": event.get("time", 0),
                                 "category": name})
            history.entries = history.entries[-MAX_LINES:]
        history.unread += 1

    def mark_read(self) -> None:
        self._history.unread = 0
        self.refresh_lists()

    def refresh_lists(self) -> None:
        self.list.clear()
        for entry in reversed(self.entries):
            suffix = " " + translate("pet_home_note_times", "×{count}").format(count=entry["count"]) \
                if entry["count"] > 1 else ""
            self.list.addItem(line(entry["event"]) + suffix)
        self.count.setText(translate("pet_home_inbox_unread", "{count} new").format(count=self.unread))
        self.page._refresh_pending()
