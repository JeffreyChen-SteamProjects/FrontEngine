"""Return one live pet to a selected work area without activating its window."""
from PySide6.QtCore import Qt


def clamp_into(pet, area) -> None:
    """Keep the whole pet inside a work area without changing its size."""
    x = min(max(pet.x(), area.x()), area.x() + area.width() - pet.width())
    y = min(max(pet.y(), area.y()), area.y() + area.height() - pet.height())
    if (x, y) != (pet.x(), pet.y()):
        pet.move(x, y)


def follow_screen(pet, size: tuple[int, int]) -> None:
    """After the pet changes monitor: restore its logical size and keep it on the new screen.

    Windows rescales a window by the new monitor's DPI after it crosses a DPI boundary,
    which would otherwise change the pet's logical size; the position is then clamped
    again, because the rescale can push the pet past the work area.
    """
    screen = pet.screen()
    if screen is None or pet.profile_session._closed:
        return
    if (pet.width(), pet.height()) != size:
        pet.resize(*size)
    clamp_into(pet, screen.availableGeometry())


def recover_pet(pet, screen) -> None:
    if screen is None or pet.profile_session._closed:
        raise ValueError('No active pet or available screen')
    area = screen.availableGeometry()
    if pet.width() > area.width() or pet.height() > area.height():
        raise ValueError('Pet is larger than the work area; reduce its size first')
    x = area.x() + (area.width() - pet.width()) // 2
    margin = min(12, (area.height() - pet.height()) // 2)
    y = area.y() + area.height() - pet.height() - margin
    if hasattr(pet, 'stop_toy'):
        pet.stop_toy()
    if hasattr(pet, 'motion'):
        pet._pointer_origin = None
        pet._dragging = False
        pet._last_move_delta = (0, 0)
    if hasattr(pet, '_drag_origin'):
        pet._drag_origin = None
    pet._end_petting()
    pet.profile_session.request('cancel')
    pet.placement_revision += 1
    pet.setScreen(screen)
    if hasattr(pet, 'motion'):
        pet.motion.set_bounds((area.x(), area.y(), area.x() + area.width(), area.y() + area.height()))
        pet.motion.set_platforms([])
        pet.motion.throw(0, 0)
        pet.place_for_focus(x, y)
    else:
        pet.move(x, y)
    pet.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
    pet.show()
    if hasattr(pet, 'motion'):
        pet.motion.x, pet.motion.y = float(pet.x()), float(pet.y())
