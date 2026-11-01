"""The pet home's ambient sound: one quiet loop that follows the home's weather and time of day.

Off unless the player turns it on, with its own volume (it never touches any other
sound in the application). It is silent whenever the home is not running - paused,
locked, in a meeting, or not created yet - and it follows the game clock, so a
rainy spell or nightfall changes the loop at the next tick.

The loops are package data (``ambience/*.wav``) made by ``tools/ambient_sounds.py``.
A player factory can be injected so tests never open an audio device.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Protocol

from PySide6.QtCore import QObject, QUrl

from frontengine.utils.pet_game.environment import sky, weather

FOLDER = Path(__file__).resolve().with_name("ambience")
LOOPS = ("day", "night", "rain", "snow")
DEFAULT_VOLUME = 40


class LoopPlayer(Protocol):
    def setSource(self, url: QUrl) -> None: ...
    def setLoopCount(self, count: int) -> None: ...
    def setVolume(self, volume: float) -> None: ...
    def play(self) -> None: ...
    def stop(self) -> None: ...


def _sound_effect(parent: QObject) -> LoopPlayer:
    from PySide6.QtMultimedia import QSoundEffect
    return QSoundEffect(parent)


def loop_for(home: str, time_ms: int) -> str:
    """Rain and snow win; otherwise night has crickets and the rest of the day birdsong."""
    current = weather(home, time_ms)
    if current in ("rain", "snow"):
        return current
    return "night" if sky(time_ms) == "night" else "day"


class Ambience(QObject):
    """Plays at most one loop; players are made on first use and kept until shutdown."""

    def __init__(self, player_factory: Callable[[QObject], LoopPlayer] | None = None,
                 parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._factory = player_factory or _sound_effect
        self._players: dict[str, LoopPlayer] = {}
        self.current: str | None = None
        self.enabled = False
        self.volume = DEFAULT_VOLUME

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = bool(enabled)
        if not self.enabled:
            self._stop()

    def set_volume(self, volume: int) -> None:
        self.volume = max(0, min(100, int(volume)))
        if self.current is not None:
            self._players[self.current].setVolume(self.volume / 100)
        if self.volume == 0:
            self._stop()

    def update(self, home: str | None, time_ms: int, running: bool) -> None:
        """Called each tick: the loop for this moment, or silence when the home is not running."""
        if not (self.enabled and running and home and self.volume > 0):
            self._stop()
            return
        wanted = loop_for(home, time_ms)
        if wanted == self.current:
            return
        self._stop()
        player = self._player(wanted)
        player.setVolume(self.volume / 100)
        player.play()
        self.current = wanted

    def _player(self, name: str) -> LoopPlayer:
        if name not in self._players:
            player = self._factory(self)
            player.setSource(QUrl.fromLocalFile(str(FOLDER / f"{name}.wav")))
            player.setLoopCount(-2)                 # QSoundEffect.Loop.Infinite
            self._players[name] = player
        return self._players[name]

    def _stop(self) -> None:
        if self.current is not None:
            self._players[self.current].stop()
            self.current = None

    def shutdown(self) -> None:
        """Stop and release every player; closing the page runs this, dropping it would not."""
        self._stop()
        for player in self._players.values():
            if isinstance(player, QObject):
                player.deleteLater()
        self._players.clear()
