"""Work orders: one recipe, a batch of units, and an explicit lifecycle.

States follow the plan: waiting for materials, reserved, travelling, working,
paused, settled (all units paid) and cancelled. A unit pays only when it
completes; its settlement transaction ID is ``<task>:u<unit>``, so a retried
settlement can never pay twice.
"""
from __future__ import annotations

from dataclasses import dataclass

from frontengine.utils.pet_game.catalog import Catalog
from frontengine.utils.pet_game.layout import RESIDENT_ID, check_local_id

STATES = ("waiting_materials", "reserved", "travelling", "working", "paused", "settled", "cancelled")
OPEN_STATES = ("waiting_materials", "reserved", "travelling", "working", "paused")
MAX_UNITS = 20
MAX_TASKS = 64


@dataclass
class Task:
    identifier: str
    recipe: str
    resident: str
    station: str | None
    units: int
    done: int = 0
    progress_ms: int = 0
    state: str = "waiting_materials"
    inputs_reserved: bool = False
    priority: int = 5

    @property
    def open(self) -> bool:
        return self.state in OPEN_STATES

    def settlement_id(self) -> str:
        return f"{self.identifier}:u{self.done}"

    def to_dict(self) -> dict:
        return {"id": self.identifier, "recipe": self.recipe, "resident": self.resident,
                "station": self.station, "units": self.units, "done": self.done,
                "progress_ms": self.progress_ms, "state": self.state,
                "inputs_reserved": self.inputs_reserved, "priority": self.priority}

    @classmethod
    def from_dict(cls, data: object, catalog: Catalog) -> Task:
        keys = {"id", "recipe", "resident", "station", "units", "done", "progress_ms", "state",
                "inputs_reserved", "priority"}
        if not isinstance(data, dict) or set(data) != keys:
            raise ValueError("Invalid task fields")
        recipe = catalog.recipes.get(data["recipe"])
        if recipe is None:
            raise ValueError("Unknown recipe")
        if not isinstance(data["resident"], str) or not RESIDENT_ID.fullmatch(data["resident"]):
            raise ValueError("Invalid task resident")
        station = None if data["station"] is None else check_local_id(data["station"], "f")
        units, done = data["units"], data["done"]
        if type(units) is not int or not 1 <= units <= MAX_UNITS or type(done) is not int or not 0 <= done <= units:
            raise ValueError("Invalid task units")
        progress = data["progress_ms"]
        if type(progress) is not int or not 0 <= progress < recipe.duration_ms:
            raise ValueError("Invalid task progress")
        if data["state"] not in STATES or type(data["inputs_reserved"]) is not bool:
            raise ValueError("Invalid task state")
        if type(data["priority"]) is not int or not 0 <= data["priority"] <= 9:
            raise ValueError("Invalid task priority")
        task = cls(check_local_id(data["id"], "t"), data["recipe"], data["resident"], station,
                   units, done, progress, data["state"], data["inputs_reserved"], data["priority"])
        if task.open and task.state in ("travelling", "working"):
            task.state = "paused"     # nobody is walking or working right after loading
        return task
