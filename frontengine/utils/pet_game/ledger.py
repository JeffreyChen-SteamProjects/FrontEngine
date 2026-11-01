"""Wallet and inventory with idempotent, journaled transactions.

Every change goes through ``apply`` with a transaction ID. Applying the same ID
again is a no-op, so retrying a settlement after a crash or a repeated signal
cannot pay twice. Quantities are integers and never go negative; reserved items
stay visible but cannot be spent twice.
"""
from __future__ import annotations

import re
from collections import deque
from collections.abc import Mapping

MAX_QUANTITY = 1_000_000
MAX_COINS = 1_000_000_000
APPLIED_MEMORY = 1024     # transaction IDs remembered for duplicate rejection
JOURNAL_LENGTH = 100      # recent entries shown to the player
_ITEM = re.compile(r"[a-z][a-z0-9_]{0,31}(:[a-z][a-z0-9_]{0,47})?")
_TRANSACTION = re.compile(r"[A-Za-z0-9:_.-]{1,96}")


def _check_item(name: object) -> str:
    if not isinstance(name, str) or not _ITEM.fullmatch(name):
        raise ValueError(f"Invalid item name: {name!r}")
    return name


def _check_count(value: object, maximum: int) -> int:
    if type(value) is not int or not 0 <= value <= maximum:
        raise ValueError("Quantity out of range")
    return value


class Ledger:
    """Coins, item stacks and reservations; the only writer of player wealth."""

    def __init__(self) -> None:
        self.coins = 0
        self.items: dict[str, int] = {}
        self.reserved: dict[str, int] = {}
        self._applied: deque[str] = deque(maxlen=APPLIED_MEMORY)
        self._applied_set: set[str] = set()
        self.journal: deque[dict] = deque(maxlen=JOURNAL_LENGTH)

    def count(self, item: str) -> int:
        return self.items.get(item, 0)

    def available(self, item: str) -> int:
        return self.count(item) - self.reserved.get(item, 0)

    def applied(self, transaction: str) -> bool:
        return transaction in self._applied_set

    def apply(self, transaction: str, reason: str, coins: int = 0,
              items: Mapping[str, int] | None = None) -> str:
        """Apply all deltas or none; returns accepted / duplicate / insufficient."""
        if not isinstance(transaction, str) or not _TRANSACTION.fullmatch(transaction):
            raise ValueError("Invalid transaction identity")
        if transaction in self._applied_set:
            return "duplicate"
        deltas = {_check_item(name): int(delta) for name, delta in (items or {}).items() if delta}
        if self.coins + coins < 0:
            return "insufficient"
        if any(self.available(name) + delta < 0 for name, delta in deltas.items()):
            return "insufficient"
        if self.coins + coins > MAX_COINS or any(
                self.count(name) + delta > MAX_QUANTITY for name, delta in deltas.items()):
            return "overflow"
        self.coins += coins
        for name, delta in deltas.items():
            total = self.count(name) + delta
            if total:
                self.items[name] = total
            else:
                self.items.pop(name, None)
        self._remember(transaction)
        self.journal.append({"id": transaction, "reason": reason, "coins": coins, "items": deltas})
        return "accepted"

    def _remember(self, transaction: str) -> None:
        if len(self._applied) == self._applied.maxlen:
            self._applied_set.discard(self._applied[0])
        self._applied.append(transaction)
        self._applied_set.add(transaction)

    def reserve(self, needs: Mapping[str, int]) -> bool:
        """Hold items for work in progress; all or nothing."""
        if any(self.available(name) < amount for name, amount in needs.items()):
            return False
        for name, amount in needs.items():
            self.reserved[name] = self.reserved.get(name, 0) + amount
        return True

    def release(self, needs: Mapping[str, int]) -> None:
        for name, amount in needs.items():
            left = self.reserved.get(name, 0) - amount
            if left > 0:
                self.reserved[name] = left
            else:
                self.reserved.pop(name, None)

    def to_dict(self) -> dict:
        return {"coins": self.coins, "items": dict(sorted(self.items.items())),
                "reserved": dict(sorted(self.reserved.items())),
                "applied": list(self._applied), "journal": list(self.journal)}

    @classmethod
    def from_dict(cls, data: object) -> Ledger:
        if not isinstance(data, dict) or set(data) != {"coins", "items", "reserved", "applied", "journal"}:
            raise ValueError("Invalid ledger fields")
        ledger = cls()
        ledger.coins = _check_count(data["coins"], MAX_COINS)
        for target, key in ((ledger.items, "items"), (ledger.reserved, "reserved")):
            if not isinstance(data[key], dict):
                raise ValueError("Invalid ledger stacks")
            for name, amount in data[key].items():
                target[_check_item(name)] = _check_count(amount, MAX_QUANTITY)
        if any(amount > ledger.count(name) for name, amount in ledger.reserved.items()):
            raise ValueError("Reserved more items than are held")
        applied = data["applied"]
        if (not isinstance(applied, list) or len(applied) > APPLIED_MEMORY or any(
                not isinstance(item, str) or not _TRANSACTION.fullmatch(item) for item in applied)):
            raise ValueError("Invalid applied transactions")
        for transaction in applied:
            ledger._remember(transaction)
        if not isinstance(data["journal"], list) or len(data["journal"]) > JOURNAL_LENGTH:
            raise ValueError("Invalid ledger journal")
        for entry in data["journal"]:
            ledger.journal.append(_checked_entry(entry))
        return ledger


def _checked_entry(entry: object) -> dict:
    if (not isinstance(entry, dict) or set(entry) != {"id", "reason", "coins", "items"}
            or not isinstance(entry["id"], str) or not isinstance(entry["reason"], str)
            or len(entry["reason"]) > 64 or type(entry["coins"]) is not int
            or not isinstance(entry["items"], dict)):
        raise ValueError("Invalid journal entry")
    for name, delta in entry["items"].items():
        _check_item(name)
        if type(delta) is not int:
            raise ValueError("Invalid journal delta")
    return {"id": entry["id"], "reason": entry["reason"], "coins": entry["coins"],
            "items": dict(entry["items"])}
