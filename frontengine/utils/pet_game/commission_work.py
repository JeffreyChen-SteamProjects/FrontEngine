"""Send a pet to make what a commission asks for.

A commission is handed in by itself once storage holds enough of its item. This turns
"make it happen" into one work order: it works out how many units are still missing
(counting what is stored and what open orders will already make), picks the pet best
suited to the trade - one that lives where a matching workstation is, has the skill
and, among those, carries the trait for the trade, the highest level and the fewest
open orders - and queues a work request that never interrupts what the pet is doing.

When it cannot, it says why: no recipe, locked by the home level, no workstation, too
little skill, missing materials (with the shortfall) or too many open orders. Nothing
is created in that case.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from frontengine.utils.pet_game.behaviour import refusal
from frontengine.utils.pet_game.goals import deliver, unlocked
from frontengine.utils.pet_game.jobs import MAX_UNITS
from frontengine.utils.pet_game.resident import PROFESSION_TRAITS

if TYPE_CHECKING:
    from frontengine.utils.pet_game.catalog import Recipe
    from frontengine.utils.pet_game.resident import Resident
    from frontengine.utils.pet_game.world import World

PRIORITY = 8          # above the automatic jobs (5): the requested item comes first


@dataclass
class Dispatch:
    """What sending a pet to a commission did, or why it could not."""

    result: str
    resident: str | None = None
    recipe: str | None = None
    units: int = 0
    missing: dict[str, int] = field(default_factory=dict)
    later: bool = False         # queued, but the pet is too tired to start right now


def _recipe_for(world: World, item: str) -> Recipe | None:
    makers = [recipe for recipe in world.catalog.recipes.values() if item in recipe.outputs]
    return min(makers, key=lambda recipe: (recipe.min_level, recipe.identifier)) if makers else None


def _queued(world: World, item: str) -> int:
    """How many of ``item`` the open work orders will still make."""
    total = 0
    for task in world.tasks.values():
        if task.open:
            outputs = world.catalog.recipes[task.recipe].outputs
            total += (task.units - task.done) * outputs.get(item, 0)
    return total


def _has_station(world: World, resident: Resident, profession: str) -> bool:
    return any(definition.profession == profession for _piece, definition in world.in_zone(resident.zone))


def _present(world: World, resident: Resident) -> bool:
    return not (resident.parked or resident.away or resident.zone in world.offline_zones)


def _worker(world: World, recipe: Recipe) -> tuple[Resident | None, str | None]:
    """The best pet for the recipe, or why there is none."""
    stationed = [resident for resident in world.residents.values()
                 if _present(world, resident) and _has_station(world, resident, recipe.profession)]
    if not stationed:
        return None, "no_station"
    skilled = [resident for resident in stationed if resident.level(recipe.profession) >= recipe.min_level]
    if not skilled:
        return None, "skill_too_low"
    trait = PROFESSION_TRAITS.get(recipe.profession)
    return min(skilled, key=lambda resident: (trait not in resident.traits, -resident.level(recipe.profession),
                                              len(world.open_tasks(resident.identifier)),
                                              resident.identifier)), None


def _shortfall(world: World, recipe: Recipe, units: int) -> dict[str, int]:
    return {item: count * units - world.ledger.available(item) for item, count in recipe.inputs.items()
            if world.ledger.available(item) < count * units}


def _offer(world: World, index: int) -> dict | None:
    offers = world.progress.commissions["offers"]
    return offers[index] if 0 <= index < len(offers) and not offers[index]["done"] else None


def plan(world: World, index: int) -> Dispatch:
    """Work out what dispatching commission ``index`` would do, without changing anything."""
    offer = _offer(world, index)
    if offer is None:
        return Dispatch("unknown")
    need = offer["count"] - world.ledger.available(offer["item"]) - _queued(world, offer["item"])
    if world.ledger.available(offer["item"]) >= offer["count"]:
        return Dispatch("deliverable")
    if need <= 0:
        return Dispatch("already_queued")
    recipe = _recipe_for(world, offer["item"])
    if recipe is None:
        return Dispatch("no_recipe")
    if not unlocked(world, recipe.unlock_level):
        return Dispatch("locked", recipe=recipe.identifier)
    worker, reason = _worker(world, recipe)
    if worker is None:
        return Dispatch(reason, recipe=recipe.identifier)
    per_unit = recipe.outputs[offer["item"]]
    units = min(MAX_UNITS, -(-need // per_unit))
    missing = _shortfall(world, recipe, units)
    if missing:
        return Dispatch("missing_materials", worker.identifier, recipe.identifier, units, missing)
    return Dispatch("accepted", worker.identifier, recipe.identifier, units)


def dispatch(world: World, index: int) -> Dispatch:
    """Send the best pet to make what commission ``index`` still lacks, or hand it in when it is ready."""
    planned = plan(world, index)
    if planned.result == "deliverable":
        delivered = deliver(world, index)
        return Dispatch("delivered" if delivered in ("accepted", "duplicate") else delivered)
    if planned.result != "accepted":
        return planned
    result, _task = world.create_task(planned.recipe, planned.resident, planned.units, priority=PRIORITY)
    if result != "accepted":
        return Dispatch(result, planned.resident, planned.recipe, planned.units)
    resident = world.residents[planned.resident]
    if refusal(world, resident, "work") is None:
        if "work" not in resident.commands:          # queued: what it is doing now is never cut short
            resident.commands.append("work")
    else:
        planned.later = True
    world.emit("commission_dispatched", resident=planned.resident, recipe=planned.recipe, units=planned.units)
    return planned
