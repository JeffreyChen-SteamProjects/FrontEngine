import json
import zipfile

import pytest


def write_puppet(path, **changes):
    document = {'version': 1, 'size': [16, 16], 'drawables': [],
                'deformers': [], 'parameters': []}
    document.update(changes)
    with zipfile.ZipFile(path, 'w') as archive:
        archive.writestr('puppet.json', json.dumps(document))
    return path


def test_puppet_container_validated_before_optional_runtime(tmp_path):
    from frontengine.utils.imervue.puppet_asset import validate_puppet
    asset = validate_puppet(write_puppet(tmp_path / 'tiny.puppet'))
    assert asset['size'] == [16, 16]


@pytest.mark.parametrize('version', [2, True, '1', None])
def test_future_or_malformed_puppet_version_rejected(tmp_path, version):
    from frontengine.utils.imervue.puppet_asset import validate_puppet
    with pytest.raises(ValueError, match='version'):
        validate_puppet(write_puppet(tmp_path / 'bad.puppet', version=version))


def test_puppet_rejects_traversal_and_missing_texture(tmp_path):
    from frontengine.utils.imervue.puppet_asset import validate_puppet
    path = write_puppet(tmp_path / 'bad.puppet')
    with zipfile.ZipFile(path, 'a') as archive:
        archive.writestr('../escape.png', b'bad')
    with pytest.raises(ValueError, match='path'):
        validate_puppet(path)
    write_puppet(path, drawables=[{'texture': 'textures/absent.png'}])
    with pytest.raises(ValueError, match='texture'):
        validate_puppet(path)


def test_scene_envelope_resolves_relative_puppet_and_preserves_legacy(tmp_path):
    from frontengine.utils.scene_format.scene_document import normalize_scene, scene_envelope
    path = write_puppet(tmp_path / 'tiny.puppet')
    entries = {'pet': {'type': 'PUPPET', 'file_path': 'tiny.puppet', 'size': [64, 96]}}
    result = normalize_scene({'format': 'frontengine.scene', 'version': 1, 'entries': entries}, tmp_path)
    assert result['pet']['file_path'] == str(path.resolve())
    assert normalize_scene({'title': {'type': 'TEXT', 'text': 'hi'}})['title']['text'] == 'hi'
    assert normalize_scene(scene_envelope(result, tmp_path), tmp_path) == result


def test_scene_rejects_future_version_and_relative_escape(tmp_path):
    from frontengine.utils.scene_format.scene_document import normalize_scene
    with pytest.raises(ValueError, match='version'):
        normalize_scene({'format': 'frontengine.scene', 'version': 2, 'entries': {}})
    with pytest.raises(ValueError, match='outside'):
        normalize_scene({'pet': {'type': 'PUPPET', 'file_path': '../other.puppet'}}, tmp_path)


def test_scene_package_round_trip_and_traversal_rejection(tmp_path):
    from frontengine.utils.scene_format.scene_package import load_package, save_package
    source = write_puppet(tmp_path / 'tiny.puppet')
    path = tmp_path / 'scene.fescene'
    save_package({'pet': {'type': 'PUPPET', 'file_path': str(source)}}, path)
    entries, lease = load_package(path)
    try:
        assert entries['pet']['type'] == 'PUPPET'
        assert zipfile.is_zipfile(entries['pet']['file_path'])
    finally:
        lease.cleanup()
    with zipfile.ZipFile(path, 'a') as archive:
        archive.writestr('../../escape', b'x')
    with pytest.raises(ValueError, match='path'):
        load_package(path)


def test_reference_imervue_reader_round_trip(tmp_path):
    reader = pytest.importorskip('Imervue.puppet.document_io')
    from frontengine.utils.imervue.puppet_asset import validate_puppet
    path = write_puppet(tmp_path / 'tiny.puppet')
    document = reader.load_puppet(path)
    reader.save_puppet(document, tmp_path / 'reference.puppet')
    assert validate_puppet(tmp_path / 'reference.puppet')['size'] == [16, 16]


def test_scene_package_canonicalizes_extraction_directory_alias(tmp_path, monkeypatch):
    from pathlib import Path
    from frontengine.utils.scene_format import scene_package

    original = scene_package.tempfile.TemporaryDirectory

    class AliasedDirectory:
        def __init__(self, **kwargs):
            self.owner = original(dir=tmp_path, **kwargs)
            nested = Path(self.owner.name) / 'nested'
            nested.mkdir()
            self.name = str(nested / '..')

        def cleanup(self):
            self.owner.cleanup()

    source = write_puppet(tmp_path / 'tiny.puppet')
    package = tmp_path / 'scene.fescene'
    scene_package.save_package({'pet': {'type': 'PUPPET', 'file_path': str(source)}}, package)
    monkeypatch.setattr(scene_package.tempfile, 'TemporaryDirectory', AliasedDirectory)
    entries, lease = scene_package.load_package(package)
    resource = Path(entries['pet']['file_path'])
    try:
        assert resource.is_relative_to(Path(lease.name).resolve())
        assert zipfile.is_zipfile(resource)
    finally:
        lease.cleanup()
    assert not resource.exists()


def test_puppet_pet_uses_reference_canvas_without_imervue_preferences(tmp_path):
    pytest.importorskip('Imervue.puppet.document_io')
    from frontengine.show.pet.puppet_pet import PuppetPetWidget
    path = write_puppet(tmp_path / 'tiny.puppet')
    pet = PuppetPetWidget(path, size=(64, 96))
    assert pet.canvas.document().size == (16, 16)
    assert pet.size().width() == 64
    pet.set_ui_variable(0.5)
    assert pet.opacity == 0.5
    pet.shutdown()
    assert not pet.idle.is_enabled()
    pet.close()


def test_scene_puppet_does_not_enter_proxy_widget(tmp_path):
    from frontengine.show.scene.scene import SceneManager
    manager = SceneManager()
    manager.add_puppet({'type': 'PUPPET', 'file_path': str(write_puppet(tmp_path / 'tiny.puppet'))})
    assert manager.graphic_scene.items() == []
    assert len(manager.puppet_settings) == 1
    manager.clear()
    assert manager.puppet_settings == []


def test_pet_page_persists_puppet_script_in_preset():
    from frontengine.ui.page.pet.pet_setting_ui import PetSettingUI
    page = PetSettingUI()
    page.set_state({'pet_image_path': 'character.puppet', 'puppet_script': 'lines.petscript.json'})
    assert page.get_state()['puppet_script'] == 'lines.petscript.json'
    page.close()


def test_scene_file_import_handles_versioned_and_package_documents(tmp_path):
    from frontengine.user_setting.scene_setting import load_scene_file, scene_json
    path = tmp_path / 'scene.json'
    path.write_text(json.dumps({'format': 'frontengine.scene', 'version': 1,
                                'entries': {'title': {'type': 'TEXT', 'text': 'hi'}}}), encoding='utf-8')
    load_scene_file(path)
    assert scene_json == {'title': {'type': 'TEXT', 'text': 'hi'}}
    scene_json.clear()


@pytest.mark.parametrize("changes", [{"x": float("nan")}, {"size": [16, -1]}, {"motion": []}, {"opacity": 101}])
def test_scene_rejects_invalid_puppet_layout(tmp_path, changes):
    from frontengine.utils.scene_format.scene_document import normalize_scene
    entry = {"type": "PUPPET", "file_path": "tiny.puppet", **changes}
    with pytest.raises(ValueError):
        normalize_scene({"pet": entry}, tmp_path)


def test_package_writer_refuses_self_unreadable_size(tmp_path, monkeypatch):
    from frontengine.utils.scene_format import scene_package
    asset = tmp_path / "asset.bin"
    asset.write_bytes(b"123456789")
    monkeypatch.setattr(scene_package, "MAX_ARCHIVE_BYTES", 8, raising=False)
    with pytest.raises(ValueError):
        scene_package.save_package({"image": {"type": "IMAGE", "file_path": str(asset)}}, tmp_path / "out.fescene")
    assert not (tmp_path / "out.fescene").exists()


@pytest.mark.parametrize('member', ['assets/missing.png', 'assets/'])
def test_package_import_requires_existing_file_asset(tmp_path, member):
    from frontengine.utils.scene_format.scene_package import load_package
    path = tmp_path / 'missing.fescene'
    with zipfile.ZipFile(path, 'w') as archive:
        archive.writestr('scene.json', json.dumps({'image': {'type': 'IMAGE', 'file_path': member}}))
        archive.writestr('assets/', b'')
    with pytest.raises(ValueError, match='resource'):
        load_package(path)


def test_corrupt_scene_package_has_boundary_error(tmp_path):
    from frontengine.utils.scene_format.scene_package import load_package
    source = tmp_path / 'broken.fescene'
    source.write_bytes(b'not a zip')
    with pytest.raises(ValueError, match='Invalid scene package'):
        load_package(source)
