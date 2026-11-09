"""The desktop pet page starts with one click: a character card puts a dressed pet on the desktop,
the pets there are listed with wardrobe / bring back / put away, and the rest is folded away."""
from PySide6.QtCore import QCoreApplication, QEvent

from frontengine.show.pet.desktop_pet import DesktopPetWidget
from frontengine.show.pet.inkside.library import VERSION, builtin_names
from frontengine.show.pet.pet_profile_session import PetProfileSession
from frontengine.ui.page.layout_kit import Section
from frontengine.user_setting.pet_profiles import PetProfiles


def _page(tmp_path, monkeypatch, *, lifetime_factory):
    from frontengine.ui.page.pet.pet_setting_ui import PetSettingUI
    monkeypatch.chdir(tmp_path)
    lifetime_factory()
    page = PetSettingUI(lifetime=lifetime_factory())
    page.profile_controls.profiles = PetProfiles({}, lambda: None)
    page.profile_controls.refresh()
    monkeypatch.setattr(page, "_target_geometry", lambda: None)
    return page


def _close(page):
    for pet in list(page.pet_list):
        pet.close()
    page.close()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_the_page_opens_with_the_cards_and_everything_else_folded(tmp_path, monkeypatch, *, lifetime_factory):
    lifetime_factory()
    page = _page(tmp_path, monkeypatch, lifetime_factory=lifetime_factory)
    try:
        sections = page.findChildren(Section)
        titles = [section.toggle_button.isHidden() for section in sections]
        assert titles[0] is True                                  # the quick start is always open
        folded = [section for section in sections[1:] if not section.toggle_button.isChecked()]
        assert len(folded) >= 7                                   # sources, looks, behaviour, sound, focus...
        assert set(page.quick.cards) == {identifier for identifier, _name in builtin_names()}
        assert all(not card.icon().isNull() for card in page.quick.cards.values())
        assert not hasattr(page.quick, "own_picture")            # pets are layered only: no picture card
        assert not hasattr(page, "choose_pack_button") and not hasattr(page, "pack_editor_button")
        assert page.quick.empty.isVisibleTo(page) and not page.quick.pets.isVisibleTo(page)
        assert not page.quick.wardrobe_button.isEnabled()
    finally:
        _close(page)


def test_a_card_puts_a_dressed_pet_on_the_desktop_in_one_click(tmp_path, monkeypatch, *, lifetime_factory):
    lifetime_factory()
    page = _page(tmp_path, monkeypatch, lifetime_factory=lifetime_factory)
    try:
        page.quick.cards["inkside-pip"].click()
        assert page.lifetime.pool().waitForDone(120000)
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


def test_the_list_brings_a_pet_back_and_puts_it_away(tmp_path, monkeypatch, *, lifetime_factory):
    lifetime_factory()
    page = _page(tmp_path, monkeypatch, lifetime_factory=lifetime_factory)
    try:
        pet = DesktopPetWidget(profiles=page.profile_controls.profiles, talk=False,
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


def test_start_with_nothing_chosen_dresses_the_pet_as_its_stable_built_in(tmp_path, monkeypatch, *, lifetime_factory):
    """A pet without a character (new, or from before pets were layered only) wears the built-in the
    home already draws it as, installed first; its profile then keeps that character."""
    from frontengine.show.pet_game.resident_art import fallback_character
    lifetime_factory()
    page = _page(tmp_path, monkeypatch, lifetime_factory=lifetime_factory)
    try:
        record = page.profile_controls.profiles.create("Old picture pet")
        page.profile_controls.refresh(selected=record["id"])
        page.start_play_pet()
        assert page.pet_list == [] and page._waiting                 # its character installs first
        assert page.lifetime.pool().waitForDone(120000)
        QCoreApplication.processEvents()
        assert [pet.profile_session.identifier for pet in page.pet_list] == [record["id"]]
        wanted = {"id": fallback_character(record["id"]), "version": VERSION}
        assert page.profile_controls.profiles.get(record["id"])["appearance"]["character"] == wanted
        assert page.pet_list[0]._current_pixmap() is not None
    finally:
        _close(page)


def test_only_a_puppet_model_is_taken_from_a_drop_a_recent_file_or_a_preset(tmp_path, monkeypatch, *,
                                                                          lifetime_factory):
    lifetime_factory()
    page = _page(tmp_path, monkeypatch, lifetime_factory=lifetime_factory)
    spawned = []
    monkeypatch.setattr(page, "start_play_pet", lambda: spawned.append(page.pet_image_path))
    try:
        for picture in ("cat.png", "walk.gif", str(tmp_path)):
            page._on_file_dropped(str(tmp_path / picture))
            page.set_state({"pet_image_path": str(tmp_path / picture)})
        assert spawned == [] and page.pet_image_path is None
        page._choose_character("inkside-pip")
        page._on_file_dropped(str(tmp_path / "rig.puppet"))
        assert spawned == [str(tmp_path / "rig.puppet")]
        assert page._chosen_character is None
        assert all(page.recent_files_combobox.itemData(index) in (None, str(tmp_path / "rig.puppet"))
                   for index in range(page.recent_files_combobox.count()))
    finally:
        _close(page)
