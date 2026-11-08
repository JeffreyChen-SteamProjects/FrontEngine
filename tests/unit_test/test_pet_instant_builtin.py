"""A character card puts the pet on the desktop before its wardrobe is installed."""
import threading
from threading import Event

from frontengine.show.pet.asset_library import PetAssetLibrary
from frontengine.show.pet.inkside.assemble import garment_identifier
from frontengine.show.pet.inkside.garments import GARMENTS
from frontengine.show.pet.inkside.library import VERSION, _template, install_builtin
from frontengine.ui.dialog.pet_asset_install import PetBuiltinSprite

CHARACTER = 'inkside-pip'


def _wardrobe_installed(library) -> int:
    template = _template(CHARACTER)
    return sum(library.is_installed(garment_identifier(garment, template), VERSION) for garment in GARMENTS)


def test_the_pet_is_ready_before_the_wardrobe_and_the_wardrobe_follows(tmp_path):
    library = PetAssetLibrary(tmp_path / 'pet-assets')
    job = PetBuiltinSprite(library, CHARACTER, tmp_path / 'previews')
    seen = []
    job.signals.finished.connect(lambda preview, error: seen.append(
        (preview, error, library.is_installed(CHARACTER, VERSION), _wardrobe_installed(library))))
    job.run()
    (preview, error, character_ready, wardrobe_at_ready), = seen
    assert error == '' and preview.endswith(f'{CHARACTER}.png')
    assert character_ready
    assert wardrobe_at_ready == 0
    assert _wardrobe_installed(library) == len(GARMENTS)


def test_cancelling_after_the_pet_appeared_stops_the_wardrobe_quietly(tmp_path):
    library = PetAssetLibrary(tmp_path / 'pet-assets')
    job = PetBuiltinSprite(library, CHARACTER, tmp_path / 'previews')
    errors = []
    job.signals.finished.connect(lambda _preview, error: (errors.append(error), job.cancel.set()))
    job.run()
    assert errors == ['']
    assert library.is_installed(CHARACTER, VERSION)
    assert _wardrobe_installed(library) < len(GARMENTS)


def test_two_installs_of_the_same_character_at_once_both_succeed(tmp_path):
    library = PetAssetLibrary(tmp_path / 'pet-assets')
    failures = []

    def install():
        try:
            install_builtin(library, CHARACTER, Event())
        except (OSError, ValueError) as error:
            failures.append(error)

    threads = [threading.Thread(target=install) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(120)
    assert failures == []
    assert library.is_installed(CHARACTER, VERSION)
    assert _wardrobe_installed(library) == len(GARMENTS)


def test_closing_the_page_also_cancels_a_wardrobe_still_installing(tmp_path, *, lifetime_factory):
    from frontengine.ui.page.pet.pet_setting_ui import PetSettingUI
    lifetime_factory()
    page = PetSettingUI(lifetime=lifetime_factory())
    try:
        job = PetBuiltinSprite(PetAssetLibrary(tmp_path / 'pet-assets'), CHARACTER, tmp_path / 'previews')
        page._sprite_install = job
        page._builtin_character_ready(str(tmp_path / 'preview.png'), '')
        assert page._sprite_install is None
        assert not job.cancel.is_set()
        page.stop_asset_preparation()
        assert job.cancel.is_set()
    finally:
        page.close()
