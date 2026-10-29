"""Temporary focus modes with ownership checks and completion deduplication."""
from dataclasses import dataclass
from frontengine.show.pet.focus_placement import Placement, park_companions, restore_placement


@dataclass
class _Participant:
    pet: object
    previous_mode: str
    revision: int
    placement: Placement | None = None


class FocusCompanions:
    """Use the existing focus timer; never overwrite a user's later mode choice."""

    def __init__(self, bounds_provider=None) -> None:
        self._participants = []
        self._completed = 0
        self._bounds_provider = bounds_provider

    @staticmethod
    def _available(pet) -> bool:
        try:
            return pet.isVisible() and not pet.profile_session._closed
        except RuntimeError:
            return False

    def begin(self, pets) -> None:
        self.stop()
        self._completed = 0
        for pet in pets:
            session = pet.profile_session
            if not self._available(pet) or session.companion.action is not None:
                continue
            previous = session.companion.mode
            session.set_mode('work')
            self._participants.append(_Participant(pet, previous, session.mode_revision))
        placements = park_companions([item.pet for item in self._participants], self._bounds_provider)
        for participant in self._participants:
            participant.placement = placements.get(id(participant.pet))

    @staticmethod
    def _owned(participant) -> bool:
        session = participant.pet.profile_session
        return (not session._closed and session.mode_revision == participant.revision
                and session.companion.action is None)

    def transition(self, phase: str, completed: int) -> None:
        if phase not in ('focus', 'break', 'long_break'):
            return
        award = phase != 'focus' and completed > self._completed
        self._completed = max(self._completed, completed)
        retained = []
        for participant in self._participants:
            if not self._owned(participant):
                continue
            session = participant.pet.profile_session
            rewarded = award and self._available(participant.pet) and session.reward_focus()
            mode = 'work' if phase == 'focus' else 'rest'
            if session.companion.mode != mode:
                session.set_mode(mode)
            if rewarded:
                session.present('celebrate')
            participant.revision = session.mode_revision
            retained.append(participant)
        self._participants = retained

    def stop(self) -> None:
        participants, self._participants = self._participants, []
        for participant in participants:
            if self._owned(participant):
                restore_placement(participant.pet, participant.placement)
                participant.pet.profile_session.set_mode(participant.previous_mode)
