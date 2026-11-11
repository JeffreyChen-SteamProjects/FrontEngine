"""What in the home is waiting for the player, as short lines that open the tab where it is handled.

The home runs itself, so this list stays short: only things the home cannot settle
on its own - no pet yet, unread inbox notes, furniture left in storage, jobs
waiting for materials, a grubby pet in a home without a bath tub, a pet's wish
and a celebration that is ready.
"""
from __future__ import annotations

from frontengine.utils.multi_language.retranslate import translate
from frontengine.utils.pet_game import goals
from frontengine.utils.pet_game.behaviour import LOW_HYGIENE

MAX_PENDING = 5


def pending(world, unread: int = 0) -> list[tuple[str, str]]:
    """``(text, tab key)`` pairs, most useful first; empty when nothing waits."""
    if world is None:
        return []
    items: list[tuple[str, str]] = []
    if not world.residents:
        items.append((translate("pet_home_pending_move_in", "Move a pet into the home"),
                      "pet_home_residents_section"))
    if unread:
        items.append((translate("pet_home_pending_unread", "{count} new notes in the inbox").format(count=unread),
                      "pet_home_inbox_section"))
    stored = sum(world.stored(definition) for definition in world.catalog.furniture)
    if stored and not world.sandbox:
        items.append((translate("pet_home_pending_storage", "{count} pieces of furniture wait in storage")
                      .format(count=stored), "pet_home_layout_section"))
    waiting = sum(1 for task in world.tasks.values() if task.state == "waiting_materials")
    if waiting:
        items.append((translate("pet_home_pending_materials", "{count} jobs wait for materials")
                      .format(count=waiting), "pet_home_shop_section"))
    grubby = _grubby_without_tub(world)
    if grubby is not None:
        items.append((translate("pet_home_pending_wash", "{name} needs a wash: a bath tub from the shop helps")
                      .format(name=grubby), "pet_home_shop_section"))
    if goals.celebration_ready(world):
        items.append((translate("pet_home_pending_celebration", "A home celebration is ready"),
                      "pet_home_goals_section"))
    for identifier in sorted(world.residents):
        wish = world.progress.wishes.get(identifier, {}).get("wish")
        if wish:
            items.append((translate("pet_home_pending_wish", "{name} has a wish").format(
                name=world.residents[identifier].name), "pet_home_residents_section"))
            break
    return items[:MAX_PENDING]


def _grubby_without_tub(world) -> str | None:
    """The first pet low on cleanliness in a home with nowhere to bathe; tidying up alone is slow."""
    if world.sandbox or any(world.definition(piece).activity == "wash" for piece in world.furniture.values()):
        return None
    for identifier in sorted(world.residents):
        resident = world.residents[identifier]
        if resident.needs["hygiene"] <= LOW_HYGIENE:
            return resident.name
    return None
