"""Residents drawn as their pets: semantic activities mapped onto the layered character renderer.

The world only says what a resident is doing (sleep, eat, work, walk to the
desk…). This module turns that into one of the layered character's actions,
so a pet without a work animation still sits at its desk instead of failing.
Renderers are prepared on the global thread pool (scanning the asset library
and decoding images is file work) and handed back through a queued signal; until
then, and for pets without a layered character, views draw the usual marker.
"""
from __future__ import annotations

import hashlib
import json
import tempfile
import weakref
from pathlib import Path
from time import monotonic
from typing import Callable

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtGui import QImage

from frontengine.show.pet.inkside.library import install_builtin, upgrade_builtin
from frontengine.utils.logging.loggin_instance import front_engine_logger

# Semantic activity -> layered action. The renderer itself falls back to idle
# for any action a character does not have.
USING_ACTIONS = {"sleep": "sleep", "nap": "sleep", "eat": "feed", "snack": "feed", "work": "sit",
                 "relax": "sit", "play": "play", "greet": "greet", "drag": "drag", "wait": "idle",
                 "idle": "idle", "wander": "idle", "visit": "idle", "help": "greet",
                 "come": "greet", "tag": "play"}
# Work shown with the profession's own pose when the character has it (built-in characters
# undressed, as whole-body frames); everyone else keeps sitting at the station.
PROFESSION_ACTIONS = {"writing": "write", "gardening": "garden", "crafting": "craft"}


def semantic_action(resident, world=None, renderer=None) -> str:
    """What the character should be doing: walking while on the way, otherwise the activity's pose."""
    activity = resident.activity
    if activity is None:
        return "idle"
    if activity.phase == "moving" and activity.kind != "drag":
        return "walk"
    if activity.kind == "work" and world is not None and renderer is not None:
        pose = PROFESSION_ACTIONS.get(_profession(world, activity.task))
        if pose is not None and renderer.has_action(pose):
            return pose
    return USING_ACTIONS.get(activity.kind, "idle")


def _profession(world, task_id: str | None) -> str | None:
    task = world.tasks.get(task_id) if task_id is not None else None
    recipe = world.catalog.recipes.get(task.recipe) if task is not None else None
    return recipe.profession if recipe is not None else None


def _deliver(owner_ref, identifier: str, key: str, result) -> None:
    """Hand the result to the owner when it still exists.

    Workers hold only a weak reference: a worker dropping the last reference would destroy a
    GUI-thread QObject on the pool thread, which crashes the process.
    """
    owner = owner_ref()
    if owner is None or owner.closed:
        return
    try:
        owner.prepared.emit(identifier, key, result)
    except RuntimeError:          # the owner went away while this ran
        pass


class _Prepare(QRunnable):
    def __init__(self, owner: ResidentArt, identifier: str, appearance: dict, key: str) -> None:
        super().__init__()
        self.owner_ref, self.library_factory = weakref.ref(owner), owner.library_factory
        self.identifier, self.appearance, self.key = identifier, appearance, key

    def run(self) -> None:
        upgraded = None
        try:
            library = self.library_factory()
            upgraded = upgrade_builtin(self.appearance)
            if upgraded is not None:          # an older built-in: install the current one first
                install_builtin(library, upgraded["character"]["id"])
            catalog, _errors = library.scan()
            renderer = catalog.prepare(upgraded or self.appearance)
        except (OSError, ValueError) as error:
            front_engine_logger.warning(f"[PetHome] appearance for {self.identifier}: {error}")
            renderer, upgraded = None, None
        _deliver(self.owner_ref, self.identifier, self.key, (renderer, self.appearance, upgraded))


FALLBACK_PREFIX = "fallback:"


def fallback_character(identifier: str) -> str:
    """The built-in character a pet without one is drawn as in the home: stable per pet, never saved."""
    from frontengine.show.pet.inkside.library import builtin_names
    names = [ident for ident, _name in builtin_names()]
    return names[int(hashlib.sha256(identifier.encode("utf-8")).hexdigest(), 16) % len(names)]


class _PrepareFallback(QRunnable):
    """Build the built-in character in a temporary folder and load it; nothing is installed or saved."""

    def __init__(self, owner: ResidentArt, identifier: str, key: str) -> None:
        super().__init__()
        self.owner_ref, self.identifier, self.key = weakref.ref(owner), identifier, key

    def run(self) -> None:
        from frontengine.show.pet.inkside.assemble import build_character
        from frontengine.show.pet.inkside.library import _template
        from frontengine.show.pet.layered_renderer import LayeredRenderer
        from frontengine.utils.pet_pack.layered import load_layered_asset
        try:
            template = _template(self.key.removeprefix(FALLBACK_PREFIX))
            with tempfile.TemporaryDirectory(prefix="frontengine-home-") as folder:
                asset = load_layered_asset(build_character(template, Path(folder).resolve() / template.ident))
                renderer = LayeredRenderer(asset)        # decodes every image now; the folder can go
        except (OSError, ValueError) as error:
            front_engine_logger.warning(f"[PetHome] stand-in character for {self.identifier}: {error}")
            renderer = None
        _deliver(self.owner_ref, self.identifier, self.key, (renderer, None, None))


class ResidentArt(QObject):
    """Per-resident renderers, prepared off the GUI thread and refreshed when an outfit changes."""

    prepared = Signal(str, str, object)
    changed = Signal()

    def __init__(self, service, library_factory: Callable | None = None,
                 pool: QThreadPool | None = None) -> None:
        super().__init__()
        self.service = service
        self.library_factory = library_factory or _default_library
        if pool is None:                  # its own pool, so closing waits only for this home's work
            pool = QThreadPool(self)
            pool.setMaxThreadCount(2)
        self.pool = pool
        self.closed = False
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
        """The ready renderer for this resident's outfit, or a built-in stand-in; None while loading."""
        appearance = self._appearance(identifier)
        if appearance is None or appearance.get("character") is None:
            return self._fallback(identifier)
        key = json.dumps(appearance, sort_keys=True)
        cached = self._renderers.get(identifier)
        if cached is not None and cached[0] == key:
            return cached[1]
        session = self.service.sessions.get(identifier)
        live = getattr(session, "appearance_renderer", None)
        current = upgrade_builtin(appearance) is None      # older built-ins are upgraded first
        if current and live is not None and (cached is None or cached[1] is not live):
            self._renderers[identifier] = (key, live)      # the wardrobe or a desktop pet prepared it
            return live
        if key not in self._pending:
            self._pending.add(key)
            self.pool.start(_Prepare(self, identifier, appearance, key))
        return cached[1] if cached is not None else None

    def _fallback(self, identifier: str):
        """Pets without a layered character (picture pets, new pets) still appear as a character here."""
        key = FALLBACK_PREFIX + fallback_character(identifier)
        cached = self._renderers.get(identifier)
        if cached is not None and cached[0] == key:
            return cached[1]
        if key not in self._pending:
            self._pending.add(key)
            self.pool.start(_PrepareFallback(self, identifier, key))
        return None

    def shutdown(self) -> None:
        """Drop queued work and wait for running work, so nothing outlives the home page."""
        self.closed = True
        self.pool.clear()
        self.pool.waitForDone()

    def _adopt(self, identifier: str, key: str, result) -> None:
        renderer, expected, upgraded = result
        self._pending.discard(key)
        if key.startswith(FALLBACK_PREFIX):     # a stand-in for the home only, never the pet's own look
            self._renderers[identifier] = (key, renderer)
            self.changed.emit()
            return
        session = self.service.sessions.get(identifier)
        if upgraded is not None and session is not None and renderer is not None:
            try:                              # an explicit, stale-checked appearance change
                session.apply_appearance(expected, upgraded, renderer, present=False)
                key = json.dumps(upgraded, sort_keys=True)
            except ValueError as error:       # changed meanwhile: the next frame prepares again
                front_engine_logger.warning(f"[PetHome] upgrade for {identifier}: {error}")
                renderer = None
        self._renderers[identifier] = (key, renderer)
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
            action = semantic_action(resident, self.service.world, renderer)
            return renderer.render(action, elapsed, mirrored=resident.facing < 0)
        except (KeyError, ValueError) as error:
            front_engine_logger.warning(f"[PetHome] frame for {resident.identifier}: {error}")
            return None


def _default_library():
    from frontengine.show.pet.asset_library import PetAssetLibrary
    return PetAssetLibrary()
