"""Return one live pet to a selected work area without activating its window."""
from PySide6.QtCore import Qt


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
