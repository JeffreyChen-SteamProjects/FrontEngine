"""Undoable scene edits that preserve legacy and unknown entry fields."""
from __future__ import annotations

import copy
import math

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QUndoCommand, QUndoStack

from frontengine.utils.scene_format.scene_document import normalize_scene


def validate_geometry(entries: dict) -> dict:
    entries = normalize_scene(entries)
    for entry in entries.values():
        for key in ("x", "y", "z", "width", "height", "scale", "rotation", "opacity"):
            if key not in entry:
                continue
            value = entry[key]
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
                raise ValueError(f"Scene {key} must be finite")
            if key in ("width", "height") and not 16 <= value <= 8192:
                raise ValueError("Scene dimensions must be between 16 and 8192")
            if key == "scale" and not 0.01 <= value <= 100:
                raise ValueError("Scene scale must be between 0.01 and 100")
            if key == "opacity" and not 0 <= value <= 100:
                raise ValueError("Scene opacity must be between 0 and 100")
        for key in ("locked", "visible"):
            if key in entry and type(entry[key]) is not bool:
                raise ValueError(f"Scene {key} must be boolean")
    return entries


class SceneEdit(QUndoCommand):
    def __init__(self, document, before: dict, after: dict, label: str) -> None:
        super().__init__(label)
        self.document, self.before, self.after = document, before, after

    def undo(self) -> None:
        self.document._apply(self.before)

    def redo(self) -> None:
        self.document._apply(self.after)


class SceneEditorDocument(QObject):
    changed = Signal(object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.entries = {}
        self.undo = QUndoStack(self)
        self.undo.setUndoLimit(100)

    def reset(self, entries: dict) -> None:
        validated = validate_geometry(entries)
        self.undo.clear()
        self._apply(validated)

    def _apply(self, entries: dict) -> None:
        self.entries = copy.deepcopy(entries)
        self.changed.emit(copy.deepcopy(self.entries))

    def replace(self, entries: dict, label: str = "Edit scene") -> None:
        after = validate_geometry(entries)
        if after != self.entries:
            self.undo.push(SceneEdit(self, copy.deepcopy(self.entries), after, label))

    def update(self, key: str, changes: dict, label: str = "Edit layer") -> None:
        if key not in self.entries:
            raise ValueError("Scene layer does not exist")
        after = copy.deepcopy(self.entries)
        after[key].update(changes)
        self.replace(after, label)

    def add(self, entry: dict, label: str = "Add layer") -> str:
        index = 1
        while "layer_" + str(index) in self.entries:
            index += 1
        key = "layer_" + str(index)
        after = copy.deepcopy(self.entries)
        after[key] = {"x": 0, "y": 0, "width": 320, "height": 180,
                      "z": len(after), "opacity": 100, "visible": True, "locked": False, **entry}
        self.replace(after, label)
        return key

    def remove(self, key: str) -> None:
        after = copy.deepcopy(self.entries)
        after.pop(key)
        self.replace(after, "Remove layer")

    def duplicate(self, key: str) -> str:
        entry = copy.deepcopy(self.entries[key])
        entry.update(x=entry.get("x", 0) + 20, y=entry.get("y", 0) + 20)
        return self.add(entry, "Duplicate layer")

    def align(self, keys: list[str], direction: str, canvas: tuple[int, int] = (1920, 1080)) -> None:
        if direction not in ("left", "center", "right", "top", "middle", "bottom"):
            raise ValueError("Unknown scene alignment")
        after = copy.deepcopy(self.entries)
        for key in keys:
            entry = after[key]
            if entry.get("locked"):
                continue
            width, height = entry.get("width", 320) * entry.get("scale", 1), entry.get("height", 180) * entry.get("scale", 1)
            if direction in ("left", "center", "right"):
                entry["x"] = {"left": 0, "center": (canvas[0] - width) / 2, "right": canvas[0] - width}[direction]
            else:
                entry["y"] = {"top": 0, "middle": (canvas[1] - height) / 2, "bottom": canvas[1] - height}[direction]
        self.replace(after, "Align layers")
