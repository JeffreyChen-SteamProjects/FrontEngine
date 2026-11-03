"""The desktop pet page starts with one click: a character card puts a dressed pet on the desktop,
the pets there are listed with wardrobe / bring back / put away, and the rest is folded away."""
from PySide6.QtCore import QCoreApplication, QEvent, QThreadPool
from PySide6.QtWidgets import QToolButton

from frontengine.show.pet.desktop_pet import DesktopPetWidget
from frontengine.show.pet.inkside.library import VERSION, builtin_names
from frontengine.show.pet.pet_profile_session import PetProfileSession
from frontengine.ui.page.layout_kit import Section
from frontengine.user_setting.pet_profiles import PetProfiles


def _page(tmp_path, monkeypatch):
    from frontengine.ui.page.pet.pet_setting_ui import PetSettingUI
    monkeypatch.chdir(tmp_path)
    page = PetSettingUI()
    page.profile_controls.profiles = PetProfiles({}, lambda: None)
    page.profile_controls.refresh()
    monkeypatch.setattr(page, "_target_geometry", lambda: None)
    return page


def _close(page):
    for pet in list(page.pet_list):
        pet.close()
    page.close()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_the_page_opens_with_the_cards_and_everything_else_folded(tmp_path, monkeypatch):
    page = _page(tmp_path, monkeypatch)
    try:
        sections = page.findChildren(Section)
        titles = [section.toggle_button.isHidden() for section in sections]
        assert titles[0] is True                                  # the quick start is always open
        folded = [section for section in sections[1:] if not section.toggle_button.isChecked()]
        assert len(folded) >= 7                                   # sources, looks, behaviour, sound, focus...
        assert set(page.quick.cards) == {identifier for identifier, _name in builtin_names()}
        assert all(not card.icon().isNull() for card in page.quick.cards.values())
        assert isinstance(page.quick.own_picture, QToolButton)
        assert page.quick.empty.isVisibleTo(page) and not page.quick.pets.isVisibleTo(page)
        assert not page.quick.wardrobe_button.isEnabled()
    finally:
        _close(page)


def test_a_card_puts_a_dressed_pet_on_the_desktop_in_one_click(tmp_path, monkeypatch):
    page = _page(tmp_path, monkeypatch)
    try:
        page.quick.cards["inkside-pip"].click()
        assert QThreadPool.globalInstance().waitForDone(120000)
        QCoreApplication.processEvents()
        assert len(page.pet_list) == 1
        pet = page.pet_list[0]
        assert type(pet) is DesktopPetWidget
        assert pet.profile_session.state()["appearance"]["character"] == {"id": "inkside-pip", "version": VERSION}
        page.quick.refresh()
        assert page.quick.pets.count() == 1
        assert page.quick.selected() == pet.profile_session.identifier
        assert page.quick.wardrobe_button.isEnabled()
    finally:
        _close(page)


def test_the_list_brings_a_pet_back_and_puts_it_away(tmp_path, monkeypatch):
    from test_pet_profile_sessions import _sprite
    page = _page(tmp_path, monkeypatch)
    try:
        pet = DesktopPetWidget(_sprite(tmp_path), profiles=page.profile_controls.profiles, talk=False,
                               sit_on_windows=False)
        page.pet_list.append(pet)
        pet.show()
        page.quick.refresh()
        identifier = pet.profile_session.identifier
        area = pet.screen().availableGeometry()
        pet.move(area.right() + 500, area.bottom() + 500)                 # lost off screen
        page.quick.bring_back()
        assert area.contains(pet.geometry())
        page.quick.put_away()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        assert PetProfileSession.active(page.profile_controls.profiles, identifier) is None
        page.quick.refresh()
        assert page.quick.pets.count() == 0
    finally:
        _close(page)
