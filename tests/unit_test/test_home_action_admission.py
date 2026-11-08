"""Home panel actions do not cross an owner's shutdown preparation boundary."""
import pytest

from frontengine.ui.page.pet_game.home_page import PetHomePage


@pytest.mark.parametrize('action', ['photo', 'album', 'wardrobe', 'new_pet'])
def test_home_panel_actions_are_rejected_during_prepare(action, lifetime_factory, monkeypatch):
    from PySide6.QtGui import QDesktopServices
    lifetime = lifetime_factory()
    page = PetHomePage(lifetime=lifetime)
    page.create_home()
    page.service.pause('test')
    residents = set(page.service.world.residents)
    opened = []
    monkeypatch.setattr(QDesktopServices, 'openUrl', lambda url: opened.append(url.toLocalFile()))
    actions = {'photo': page.goals.take_photo, 'album': page.collection._open_album,
               'wardrobe': page.residents.wardrobe, 'new_pet': page.residents.new_pet}
    try:
        lifetime.begin_prepare()
        actions[action]()
        assert not list(page.collection.folder().glob('*.png'))
        assert opened == []
        assert page.residents.wardrobes == {}
        assert set(page.service.world.residents) == residents
        lifetime.cancel_prepare()
        assert not list(page.collection.folder().glob('*.png'))
        assert opened == []
        assert page.residents.wardrobes == {}
        assert set(page.service.world.residents) == residents
        actions[action]()
        if action == 'photo':
            assert len(list(page.collection.folder().glob('*.png'))) == 1
        elif action == 'album':
            assert opened == [str(page.collection.folder()).replace('\\', '/')]
        elif action == 'wardrobe':
            assert page.selected_resident in page.residents.wardrobes
        else:
            assert len(page.service.world.residents) == len(residents) + 1
    finally:
        lifetime.cancel_prepare()
        assert page.shutdown()
        page.close()


@pytest.mark.parametrize('action', ['share', 'visit'])
def test_blueprint_dialog_result_is_discarded_when_owner_starts_closing(
        action, lifetime_factory, monkeypatch, tmp_path):
    from frontengine.utils.pet_game.blueprint import export_blueprint
    lifetime = lifetime_factory()
    page = PetHomePage(lifetime=lifetime)
    page.create_home()
    source = tmp_path / 'blueprint.json'
    if action == 'visit':
        source.write_text(export_blueprint(page.service.world), encoding='utf-8')
    def choose():
        lifetime.begin_prepare()
        return str(source)
    method = 'choose_save_path' if action == 'share' else 'choose_open_path'
    monkeypatch.setattr(page.layout_panel, method, choose)
    try:
        result = (page.layout_panel.share_blueprint() if action == 'share'
                  else page.layout_panel.visit_blueprint())
        assert result is None
        assert page.layout_panel.visits == []
        if action == 'share':
            assert not source.exists()
    finally:
        lifetime.cancel_prepare()
        assert page.shutdown()
        page.close()
