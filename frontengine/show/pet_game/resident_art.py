"""Residents drawn as their pets: semantic activities mapped onto the layered character renderer.

The world only says what a resident is doing (sleep, eat, work, walk to the
desk…). This module turns that into one of the layered character's actions,
so a pet without a work animation still sits at its desk instead of failing.
Renderers are prepared on the global thread pool (scanning the asset library
and decoding images is file work) and handed back through a queued signal; until
then, and for pets without a layered character, views draw the usual marker.
"""
from __future__ import annotations

import json
from time import monotonic
from typing import Callable

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtGui import QImage

from frontengine.utils.logging.loggin_instance import front_engine_logger

# Semantic activity -> layered action. The renderer itself falls back to idle
# for any action a character does not have.
USING_ACTIONS = {"sleep": "sleep", "nap": "sleep", "eat": "feed", "snack": "feed", "work": "sit",
                 "relax": "sit", "play": "play", "greet": "greet", "drag": "drag", "wait": "idle",
                 "idle": "idle", "wander": "idle"}


def semantic_action(resident) -> str:
    """What the character should be doing: walking while on the way, otherwise the activity's pose."""
    activity = resident.activity
    if activity is None:
        return "idle"
    if activity.phase == "moving" and activity.kind != "drag":
        return "walk"
    return USING_ACTIONS.get(activity.kind, "idle")


class _Prepare(QRunnable):
    def __init__(self, owner: ResidentArt, identifier: str, appearance: dict, key: str) -> None:
        super().__init__()
        self.owner, self.identifier, self.appearance, self.key = owner, identifier, appearance, key

    def run(self) -> None:
        try:
            catalog, _errors = self.owner.library_factory().scan()
            renderer = catalog.prepare(self.appearance)
        except (OSError, ValueError) as error:
            front_engine_logger.warning(f"[PetHome] appearance for {self.identifier}: {error}")
            renderer = None
        try:
            self.owner.prepared.emit(self.identifier, self.key, renderer)
        except RuntimeError:          # the owner went away while this ran
            pass


class ResidentArt(QObject):
    """Per-resident renderers, prepared off the GUI thread and refreshed when an outfit changes."""

    prepared = Signal(str, str, object)
    changed = Signal()

    def __init__(self, service, library_factory: Callable | None = None,
                 pool: QThreadPool | None = None) -> None:
        super().__init__()
        self.service = service
        self.library_factory = library_factory or _default_library
        self.pool = pool or QThreadPool.globalInstance()
        self._renderers: dict[str, tuple[str, object]] = {}
        self._pending: set[str] = set()
        self._started = monotonic()
        self.prepared.connect(self._adopt, Qt.ConnectionType.QueuedConnection)

    def _appearance(self, identifier: str) -> dict | None:
        session = self.service.sessions.get(identifier)
        if session is None:
            return None
        try:
            return session.state()["appearance"]
        except (OSError, ValueError, KeyError):
            return None

    def renderer(self, identifier: str):
        """The ready renderer for this resident's current outfit, or None (draw a marker)."""
        appearance = self._appearance(identifier)
        if appearance is None or appearance.get("character") is None:
            return None
        key = json.dumps(appearance, sort_keys=True)
        cached = self._renderers.get(identifier)
        if cached is not None and cached[0] == key:
            return cached[1]
        session = self.service.sessions.get(identifier)
        live = getattr(session, "appearance_renderer", None)
        if live is not None and (cached is None or cached[1] is not live):
            self._renderers[identifier] = (key, live)      # the wardrobe or a desktop pet prepared it
            return live
        if key not in self._pending:
            self._pending.add(key)
            self.pool.start(_Prepare(self, identifier, appearance, key))
        return cached[1] if cached is not None else None

    def _adopt(self, identifier: str, key: str, renderer) -> None:
        self._pending.discard(key)
        self._renderers[identifier] = (key, renderer)
        session = self.service.sessions.get(identifier)
        if session is not None and renderer is not None:
            session.appearance_renderer = renderer
        self.changed.emit()

    def frame(self, resident, still: bool = False) -> QImage | None:
        """The resident's current frame, mirrored when it faces left; None draws the marker."""
        renderer = self.renderer(resident.identifier)
        if renderer is None:
            return None
        elapsed = 0 if still else int((monotonic() - self._started) * 1000)
        try:
            return renderer.render(semantic_action(resident), elapsed, mirrored=resident.facing < 0)
        except (KeyError, ValueError) as error:
            front_engine_logger.warning(f"[PetHome] frame for {resident.identifier}: {error}")
            return None


def _default_library():
    from frontengine.show.pet.asset_library import PetAssetLibrary
    return PetAssetLibrary()
