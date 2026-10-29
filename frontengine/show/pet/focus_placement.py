"""Logical-work-area corner placement without native input or focus changes."""
from dataclasses import dataclass


def corner_positions(bounds: tuple[int, int, int, int], sizes, margin: int = 12):
    """Pack bottom-right shelves; return None when a pet cannot fit safely."""
    left, top, width, height = bounds
    right, bottom = left + width - margin, top + height - margin
    x, y, row_height = right, bottom, 0
    result = []
    for pet_width, pet_height in sizes:
        if pet_width > width - 2 * margin or pet_height > height - 2 * margin:
            result.append(None)
            continue
        if x - pet_width < left + margin:
            x, y, row_height = right, y - row_height - margin, 0
        if y - pet_height < top + margin:
            result.append(None)
            continue
        result.append((x - pet_width, y - pet_height))
        x -= pet_width + margin
        row_height = max(row_height, pet_height)
    return result


@dataclass(frozen=True)
class Placement:
    original: tuple[int, int]
    parked: tuple[int, int]
    revision: int


def _move(pet, point) -> None:
    if hasattr(pet, 'place_for_focus'):
        pet.place_for_focus(*point)
    else:
        pet.move(*point)


def park_companions(pets, bounds_provider=None) -> dict[int, Placement]:
    groups = {}
    for pet in pets:
        if bounds_provider:
            bounds = bounds_provider(pet)
        else:
            screen = pet.screen()
            if screen is None:
                continue
            area = screen.availableGeometry()
            bounds = (area.x(), area.y(), area.width(), area.height())
        if bounds is not None:
            groups.setdefault(bounds, []).append(pet)
    placements = {}
    for bounds, group in groups.items():
        positions = corner_positions(bounds, [(pet.width(), pet.height()) for pet in group])
        for pet, point in zip(group, positions):
            if point is None:
                continue
            original = (pet.x(), pet.y())
            _move(pet, point)
            placements[id(pet)] = Placement(original, point, getattr(pet, 'placement_revision', 0))
    return placements


def restore_placement(pet, placement: Placement | None) -> None:
    if (placement is not None and (pet.x(), pet.y()) == placement.parked
            and getattr(pet, 'placement_revision', 0) == placement.revision):
        # A removed/resized monitor must not restore the pet outside its current work area.
        screen = pet.screen()
        if screen is None:
            return
        area = screen.availableGeometry()
        x = max(area.x(), min(placement.original[0], area.x() + area.width() - pet.width()))
        y = max(area.y(), min(placement.original[1], area.y() + area.height() - pet.height()))
        _move(pet, (x, y))
