"""Deterministic random numbers whose whole state is one saved integer."""
from __future__ import annotations

from collections.abc import Sequence
from typing import TypeVar

_MASK = (1 << 64) - 1
_T = TypeVar("_T")


class GameRandom:
    """SplitMix64: tiny, fast and replayable from the integer kept in the save."""

    def __init__(self, state: int) -> None:
        if type(state) is not int or not 0 <= state <= _MASK:
            raise ValueError("Random state must be an unsigned 64-bit integer")
        self.state = state

    def next_u64(self) -> int:
        self.state = (self.state + 0x9E3779B97F4A7C15) & _MASK
        value = self.state
        value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & _MASK
        value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & _MASK
        return value ^ (value >> 31)

    def randint(self, low: int, high: int) -> int:
        """Inclusive bounds; the modulo bias over 2**64 is far below anything visible."""
        if high < low:
            raise ValueError("Empty random range")
        return low + self.next_u64() % (high - low + 1)

    def choice(self, items: Sequence[_T]) -> _T:
        if not items:
            raise ValueError("Cannot choose from an empty sequence")
        return items[self.randint(0, len(items) - 1)]

    def weighted(self, pairs: Sequence[tuple[_T, int]]) -> _T:
        """Pick by positive integer weights; zero weights are never chosen."""
        total = sum(weight for _item, weight in pairs if weight > 0)
        if total <= 0:
            raise ValueError("No positive weight to choose from")
        roll = self.randint(1, total)
        for item, weight in pairs:
            if weight > 0:
                roll -= weight
                if roll <= 0:
                    return item
        raise AssertionError("unreachable")  # pragma: no cover
