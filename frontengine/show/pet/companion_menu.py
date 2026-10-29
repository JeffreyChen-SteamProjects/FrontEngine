"""Shared, localized care commands for sprite and native pet windows."""
from PySide6.QtCore import QObject, Slot
from PySide6.QtGui import QAction

from frontengine.utils.multi_language.retranslate import retranslator, tr, translate
from frontengine.utils.pet_companion.stats import FOOD_SNACK, FOOD_FEAST, FOOD_MUSIC, FOOD_BOOK


def add_food_actions(menu, feed) -> dict:
    treats = menu.addMenu('')
    tr(treats, 'pet_treats', 'Treats', 'setTitle')
    actions = {}
    for kind, fallback in ((FOOD_SNACK, 'Crunchy bite'), (FOOD_FEAST, 'Hearty bowl'),
                           (FOOD_MUSIC, 'Melody biscuit'), (FOOD_BOOK, 'Page wafer')):
        action = QAction(treats)
        retranslator.bind(action, 'pet_treat_' + kind, fallback)
        action.triggered.connect(lambda _checked=False, food=kind: feed(food))
        treats.addAction(action)
        actions[kind] = action
    return actions


class _ModeChecks(QObject):
    def __init__(self, menu, session, actions):
        super().__init__(menu)
        self.session, self.actions = session, actions
        session.changed.connect(self.refresh)
        self.refresh()

    @Slot()
    def refresh(self) -> None:
        for mode in ('play', 'work', 'rest'):
            self.actions[mode].setChecked(self.session.companion.mode == mode)


def add_companion_actions(menu, session, feedback, *, request=None) -> dict:
    request = request or session.request
    actions = {}
    commands = (("greet", "Say hello"), ("pet", "Pet gently"),
                ("groom", "Groom"), ("cancel", "End interaction"))
    menu.addSeparator()
    for command, fallback in commands:
        action = QAction(menu)
        retranslator.bind(action, "pet_companion_" + command, fallback)
        action.triggered.connect(lambda _checked=False, name=command: feedback(request(name)))
        menu.addAction(action)
        actions[command] = action
    for mode, fallback in (("play", "Play together"), ("work", "Work together"), ("rest", "Rest")):
        action = QAction(menu)
        action.setCheckable(True)
        retranslator.bind(action, "pet_companion_" + mode, fallback)
        action.triggered.connect(lambda _checked=False, name=mode: feedback(session.set_mode(name)))
        menu.addAction(action)
        actions[mode] = action

    _ModeChecks(menu, session, actions)
    return actions


def companion_status(session) -> str:
    state = session.companion
    return translate("pet_companion_status", "{mode} · Energy {energy}/100").format(
        mode=translate("pet_companion_" + state.mode), energy=state.energy)
