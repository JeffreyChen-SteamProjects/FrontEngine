"""Active-time care and interactions for one persistent pet identity."""

from copy import deepcopy
from decimal import Decimal, InvalidOperation
from collections.abc import Mapping

from .stats import FOOD_EFFECTS, FOOD_SNACK, PetGrowth, PetHunger, PetMood, bond_stage


ACTION_SECONDS = {"greet": 0.75, "pet": 2, "groom": 3, "feed": 2, "play": 3}
COOLDOWN_SECONDS = {"greet": 5, "pet": 5, "groom": 60, "feed": 30, "play": 30}
CARE_SECONDS = 30
MODES = ("play", "work", "rest")
_REWARDS = {"greet": (3, 1), "pet": (12, 2), "groom": (8, 3), "play": (10, 3)}
_EVENT_AFFECTION = {"peer": 3, "tag": 1, "fetch": 1, "ball": 1}
# Closer pets greet more warmly; the semantic action and its reward stay "greet".
GREET_VISUAL = {"new": "greet", "familiar": "greet", "close": "peer_greet", "in_sync": "celebrate"}
# Cosmetic presentations and how long each plays on the active clock. The mode
# transitions match the length of their authored non-looping clips.
PRESENT_SECONDS = {"celebrate": 2, "outfit_show": 2, "food_like": 2, "food_dislike": 2,
                   "sleep_in": 1.5, "wake": 1.4}
# Playing tires a pet; resting (care ticks in rest mode) restores energy.
ENERGY_COST = {"play": 4, "ball": 2, "fetch": 2, "tag": 1}
TIRED_ENERGY = 20


def _bounded(value: object, default: int) -> int:
    try:
        return max(0, min(100, int(value)))
    except (TypeError, ValueError, OverflowError):
        return default


class CompanionState:
    """Own care values; only ``advance`` moves this instance's active clock."""

    def __init__(self, record: Mapping) -> None:
        self.mood = PetMood(_bounded(record.get("mood", 60), 60))
        self.hunger = PetHunger(_bounded(record.get("fullness", 70), 70))
        try:
            self.growth = PetGrowth(record.get("affection", 0))
        except OverflowError:
            self.growth = PetGrowth()
        self.energy = _bounded(record.get("energy", 70), 70)
        mode = record.get("mode", "play")
        self.mode = mode if mode in MODES else "play"
        preferences = record.get("preferences", {})
        self.preferences = deepcopy(dict(preferences)) if isinstance(preferences, Mapping) else {}
        self.action: str | None = None
        self._food = FOOD_SNACK
        self._food_reaction = None
        self._now = Decimal(0)
        self._next_care = Decimal(CARE_SECONDS)
        self._action_end: Decimal | None = None
        self._ready: dict[str, Decimal] = {}
        self._presentation: str | None = None
        self._presentation_end: Decimal | None = None

    def snapshot(self) -> dict:
        return {"mood": self.mood.value, "fullness": self.hunger.value,
                "affection": self.growth.affection, "energy": self.energy,
                "mode": self.mode, "preferences": deepcopy(self.preferences)}

    @property
    def allows_autonomy(self) -> bool:
        return self.mode == "play" and self.action is None and self._presentation is None

    @property
    def visual_action(self) -> str | None:
        if self.action == "greet":
            return GREET_VISUAL[self.bond]
        return self.action or self._presentation or {"rest": "sleep", "work": "sit", "play": None}[self.mode]

    @property
    def bond(self) -> str:
        return bond_stage(self.growth.affection)

    @property
    def tired(self) -> bool:
        """Low energy shows even when automatic rest is off; the pet still obeys the user."""
        return self.energy <= TIRED_ENERGY

    def present(self, action: str) -> bool:
        """Brief cosmetic reaction on the active clock, without rewards or persistence."""
        if action not in PRESENT_SECONDS or self.action is not None:
            return False
        self._presentation = action
        self._presentation_end = self._now + Decimal(str(PRESENT_SECONDS[action]))
        return True

    def set_mode(self, mode: str) -> str:
        if mode not in MODES:
            return "unsupported"
        self._cancel()
        self._enter(mode)
        return "accepted"

    def _enter(self, mode: str) -> None:
        """Change mode and play the transition between sleeping and awake poses."""
        previous, self.mode = self.mode, mode
        if mode == "rest" and previous != "rest":
            self.present("sleep_in")
        elif previous == "rest" and mode != "rest":
            self.present("wake")

    def _cancel(self) -> None:
        self.action = None
        self._action_end = None
        self._presentation = None
        self._presentation_end = None

    def request(self, action: str, kind: str = FOOD_SNACK) -> str:
        if action == "cancel":
            self._cancel()
            return "accepted"
        if action == "drag":
            self._cancel()
            self.action = "drag"
            return "accepted"
        if not isinstance(action, str) or action not in ACTION_SECONDS:
            return "unsupported"
        if action == "feed" and (not isinstance(kind, str) or kind not in FOOD_EFFECTS):
            return "unsupported"
        if self.action is not None:
            return "busy"
        if action == "feed" and self.hunger.value >= 100:
            return "full"
        if self._now < self._ready.get(action, Decimal(0)):
            return "cooldown"
        self._presentation = None
        self._presentation_end = None
        self.action, self._food = action, kind
        taste = self.preferences.get('taste', {})
        self._food_reaction = ('food_like' if kind == taste.get('favorite') else
                               'food_dislike' if kind == taste.get('disliked') else None) if action == 'feed' else None
        self._action_end = self._now + Decimal(str(ACTION_SECONDS[action]))
        return "accepted"

    def reward(self, kind: str) -> str:
        """Deduplicate semantic completions from existing peer and toy adapters."""
        if not isinstance(kind, str) or kind not in _EVENT_AFFECTION:
            return "unsupported"
        if not self.allows_autonomy:
            return "busy"
        key = "event:" + kind
        if self._now < self._ready.get(key, Decimal(0)):
            return "cooldown"
        before = self.bond
        self.growth.add(_EVENT_AFFECTION[kind])
        self._keepsake(before)
        self.energy = _bounded(self.energy - ENERGY_COST.get(kind, 0), 70)
        self._ready[key] = self._now + CARE_SECONDS
        return "accepted"

    def _complete(self) -> None:
        action = self.action
        reaction = self._food_reaction if action == 'feed' else None
        if action == "feed":
            effect = FOOD_EFFECTS[self._food]
            self.hunger.feed(effect["fullness"])
            mood, affection = effect["mood"], effect["affection"]
            if reaction == 'food_like':
                mood += 4
            elif reaction == 'food_dislike':
                mood = max(0, mood - 6)
        else:
            mood, affection = _REWARDS[action]
            self.energy = _bounded(self.energy - ENERGY_COST.get(action, 0), 70)
        self.mood.pet(mood)
        before = self.bond
        self.growth.add(affection)
        self._ready[action] = self._now + COOLDOWN_SECONDS[action]
        self._cancel()
        if reaction:
            self.present(reaction)
        self._keepsake(before)

    def _keepsake(self, before: str) -> None:
        """Reaching a closer relationship stage plays a one-time celebration."""
        if self.bond != before and self.action is None:
            self.present("celebrate")

    def _auto_rest(self) -> None:
        if (self.action is None and self.mode != "rest" and self.energy <= 10
                and self.preferences.get("auto_rest") is True):
            self._enter("rest")

    def _care(self) -> None:
        self.mood.decay()
        self.hunger.decay()
        delta = {"rest": 3, "play": -1, "work": 0}[self.mode]
        self.energy = _bounded(self.energy + delta, 70)
        self._auto_rest()

    def advance(self, seconds: float) -> None:
        """Advance active seconds, processing completions before coincident care ticks."""
        try:
            elapsed = Decimal(str(seconds))
        except (InvalidOperation, ValueError):
            raise ValueError("seconds must be finite and nonnegative") from None
        if not elapsed.is_finite() or elapsed < 0:
            raise ValueError("seconds must be finite and nonnegative")
        end = self._now + elapsed
        self._auto_rest()
        while True:
            event = min(self._next_care, self._action_end or self._next_care,
                        self._presentation_end or self._next_care)
            if event > end:
                break
            self._now = event
            if self._presentation_end == event:
                self._presentation = None
                self._presentation_end = None
            if self._action_end == event:
                self._complete()
                self._auto_rest()
            if self._next_care == event:
                self._care()
                self._next_care += CARE_SECONDS
        self._now = end
