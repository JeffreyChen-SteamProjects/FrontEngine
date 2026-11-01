"""The Qt owner of one pet home: clock, identity leases, saving and lifecycle.

One shared 200 ms timer drives the world; no furniture or resident has its own
timer. Elapsed time comes from a monotonic clock and gaps longer than a few
seconds (sleep, hibernation, a stalled event loop, a clock jump) are dropped,
not caught up, matching the pets' existing "no offline care" rule.

Each resident holds the ordinary ``PetProfileSession`` lease for its identity,
so the same pet cannot also run as a desktop pet, but the session's own care
timer is never started: the world is the only time source. Care values are
written back to the pet profile after the home save, which is the record of
truth if the second write fails.
"""
from __future__ import annotations

import secrets
import uuid
from concurrent.futures import Executor, Future
from time import monotonic
from typing import Callable, TypeVar

from PySide6.QtCore import QObject, Qt, QTimer, Signal

from frontengine.show.pet.pet_profile_session import PetProfileSession
from frontengine.user_setting.pet_game_save import HomeSaveStore, LoadResult
from frontengine.user_setting.pet_profiles import PetProfiles
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.pet_game import simulation
from frontengine.utils.pet_game.behaviour import cancel_activity
from frontengine.utils.pet_game.world import World

TICK_MS = simulation.STEP_MS
MAX_GAP_MS = 5000             # longer gaps are not simulated
SAVE_DELAY_MS = 800           # coalesces drags and bursts of commands
PERIODIC_SAVE_MS = 30000
RETRY_MS = 5000
_SAVE_EVENTS = {"settled", "placed", "arrived", "settle_failed"}
_T = TypeVar("_T")


class HomeService(QObject):
    """Commands go through ``run``; views read ``world`` and listen to signals."""

    ticked = Signal()
    events_ready = Signal(list)
    save_failed = Signal(str)
    saved = Signal()
    running_changed = Signal(bool)
    _written = Signal(object, int)      # emitted from the writer thread

    def __init__(self, parent: QObject | None, store: HomeSaveStore, profiles: PetProfiles,
                 clock: Callable[[], float] = monotonic,
                 session_factory: Callable[..., PetProfileSession] = PetProfileSession,
                 executor: Executor | None = None) -> None:
        super().__init__(parent)
        self.store, self.profiles = store, profiles
        self.world: World | None = None
        self.sessions: dict[str, PetProfileSession] = {}
        self.pause_reasons: set[str] = {"stopped"}    # nothing runs until start()
        self._clock = clock
        self._session_factory = session_factory
        self._last: float | None = None
        self._dirty = False
        self._closed = False
        self._revision = 0
        self._executor = executor      # None writes synchronously (tests)
        self._future: Future | None = None
        self._pending = False
        self._written.connect(self._on_written, Qt.ConnectionType.QueuedConnection)
        self.timer = QTimer(self)
        self.timer.setInterval(TICK_MS)
        self.timer.timeout.connect(self._tick)
        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self._save_soon)
        self.periodic = QTimer(self)
        self.periodic.setInterval(PERIODIC_SAVE_MS)
        self.periodic.timeout.connect(self._periodic_save)

    # ----- opening ----------------------------------------------------------------

    def open(self) -> LoadResult:
        """Load the saved home without creating one; a protected save stays untouched."""
        result = self.store.load()
        if result.world is not None:
            self._adopt_world(result.world)
        return result

    def restore_backup(self) -> LoadResult:
        result = self.store.restore_backup()
        if result.world is not None:
            self._adopt_world(result.world)
            self.schedule_save()
        return result

    def create_home(self, screen: str, x: int, y: int, width_cells: int, seed: int | None = None,
                    furnish: bool = False) -> World:
        """Start a new home with the starter kit (set out at once with ``furnish``); never replaces one."""
        if self.world is not None:
            raise ValueError("A home is already open")
        world = World(self.store.catalog, uuid.uuid4().hex, self.store.mode,
                      secrets.randbits(63) if seed is None else seed)
        zone = world.add_zone(screen, x, y, width_cells)
        if world.mode == "manage":
            world.grant_starter_kit()
            if furnish:
                world.furnish(zone)
        self._adopt_world(world)
        self.save_now()
        return world

    def _adopt_world(self, world: World) -> None:
        self.world = world
        for identifier in sorted(world.residents):
            resident = world.residents[identifier]
            if not self._lease(identifier):
                cancel_activity(world, resident, "active_elsewhere")
                resident.away = True

    def retry_leases(self) -> list[str]:
        """Bring back parked residents whose identity is no longer live elsewhere."""
        returned = []
        for identifier in sorted(self.world.residents if self.world else ()):
            if identifier not in self.sessions and self._lease(identifier):
                self.world.residents[identifier].away = False
                returned.append(identifier)
        return returned

    def _lease(self, identifier: str) -> bool:
        """Hold the identity like a desktop pet would; never start its care timer."""
        try:
            session = self._session_factory(self, identifier, self.profiles)
        except ValueError as error:
            front_engine_logger.warning(f"[PetHome] resident {identifier} unavailable: {error}")
            return False
        session.pause()
        self.sessions[identifier] = session
        return True

    # ----- residents --------------------------------------------------------------

    def adopt(self, identifier: str, zone: str | None = None) -> str:
        """Move a saved pet into the home; the pet must not be live elsewhere."""
        if self.world is None:
            return "no_home"
        if identifier in self.world.residents:
            return "duplicate"
        if not self._lease(identifier):
            return "active_elsewhere"
        target = zone or next(iter(self.world.zones))
        result = self.world.add_resident(self.sessions[identifier].state(), target)
        if result != "accepted":
            self.sessions.pop(identifier).close()
            return result
        self.schedule_save()
        return result

    def release(self, identifier: str) -> str:
        """Move a resident out; its care values go back to the profile first."""
        if self.world is None or identifier not in self.world.residents:
            return "unknown"
        if not self._mirror(identifier):
            return "save_failed"
        result = self.world.remove_resident(identifier)
        session = self.sessions.pop(identifier, None)
        if session is not None and not session.close():
            return "save_failed"
        self.schedule_save()
        return result

    def _mirror(self, identifier: str) -> bool:
        """Copy home-owned care values into the profile through its single session."""
        session = self.sessions.get(identifier)
        resident = self.world.residents.get(identifier) if self.world else None
        if session is None or resident is None:
            return True
        companion = session.companion
        companion.energy = resident.needs["energy"]
        companion.hunger.value = resident.needs["fullness"]
        companion.mood.value = resident.needs["mood"]
        companion.growth.affection = resident.affection
        return session.flush()

    # ----- commands and time --------------------------------------------------------

    def run(self, command: Callable[[World], _T]) -> _T:
        """Apply one player command to the world and persist it soon."""
        if self.world is None:
            raise ValueError("No home is open")
        result = command(self.world)
        self._publish()
        self.schedule_save()
        return result

    @property
    def running(self) -> bool:
        return self.timer.isActive()

    def start(self) -> None:
        self._set_paused("stopped", False)

    def pause(self, reason: str) -> None:
        self._set_paused(reason, True)

    def resume(self, reason: str) -> None:
        self._set_paused(reason, False)

    def _set_paused(self, reason: str, paused: bool) -> None:
        if paused:
            self.pause_reasons.add(reason)
        else:
            self.pause_reasons.discard(reason)
        should_run = self.world is not None and not self.pause_reasons and not self._closed
        if should_run and not self.timer.isActive():
            self._last = self._clock()
            self.timer.start()
            self.periodic.start()
            self.running_changed.emit(True)
        elif not should_run and self.timer.isActive():
            self.timer.stop()
            self.periodic.stop()
            self._last = None
            self.running_changed.emit(False)
            self.schedule_save()

    def _tick(self) -> None:
        now = self._clock()
        elapsed = int(round((now - self._last) * 1000)) if self._last is not None else 0
        self._last = now
        if 0 < elapsed <= MAX_GAP_MS and self.world is not None:
            simulation.advance(self.world, elapsed)
            self._dirty = True
        self._publish()

    def _publish(self) -> None:
        events = self.world.drain_events() if self.world is not None else []
        if events:
            self.events_ready.emit(events)
            if any(event["kind"] in _SAVE_EVENTS for event in events):
                self.schedule_save()
        self.ticked.emit()

    # ----- saving --------------------------------------------------------------------

    def schedule_save(self) -> None:
        self._dirty = True
        self._revision += 1
        if not self._closed:
            self.save_timer.start(SAVE_DELAY_MS)

    def _periodic_save(self) -> None:
        if self._dirty:
            self._save_soon()

    def _save_soon(self) -> None:
        """Encode on the GUI thread, write on the worker; one write in flight, latest wins."""
        if self._executor is None:
            self.save_now()
            return
        if self.world is None:
            return
        if self._future is not None:
            self._pending = True
            return
        try:
            data = self.store.encode(self.world)
        except ValueError as error:
            self._failed(error)
            return
        revision = self._revision
        self._future = self._executor.submit(self.store.write_encoded, data)
        self._future.add_done_callback(lambda future: self._written.emit(future.exception(), revision))

    def _on_written(self, error: object, revision: int) -> None:
        self._future = None
        if error is not None:
            self._failed(error)
        else:
            self._succeeded(revision)
        if self._pending and not self._closed:
            self._pending = False
            self._save_soon()

    def _failed(self, error: object) -> None:
        front_engine_logger.warning(f"[PetHome] save failed: {error!r}")
        self.save_failed.emit(str(error))
        if not self._closed:
            self.save_timer.start(RETRY_MS)

    def _succeeded(self, revision: int) -> bool:
        if revision == self._revision:
            self._dirty = False
        mirrored = True
        for identifier in sorted(self.sessions):      # every profile, even after a failure
            mirrored = self._mirror(identifier) and mirrored
        self.saved.emit()
        return mirrored

    def save_now(self) -> bool:
        """Blocking save (shutdown, tests): home first, then profiles; failure keeps memory."""
        self.save_timer.stop()
        if self._future is not None:
            self._future.result()   # let the in-flight write finish first; its signal is ignored
            self._future = None
        if self.world is None:
            return True
        revision = self._revision
        try:
            self.store.save(self.world)
        except (OSError, ValueError) as error:
            self._failed(error)
            return False
        return self._succeeded(revision)

    def shutdown(self) -> bool:
        """Stop time, cancel activities without rewards, save and release identities."""
        if self._closed:
            return True
        self.timer.stop()
        self.periodic.stop()
        if self.world is not None:
            for identifier in sorted(self.world.residents):
                cancel_activity(self.world, self.world.residents[identifier], "closing")
        if not self.save_now():
            return False
        for identifier in sorted(self.sessions):
            if not self.sessions[identifier].close():
                return False
            del self.sessions[identifier]
        self._closed = True
        self.save_timer.stop()
        if self._executor is not None:
            self._executor.shutdown(wait=True)
        self.running_changed.emit(False)
        return True
