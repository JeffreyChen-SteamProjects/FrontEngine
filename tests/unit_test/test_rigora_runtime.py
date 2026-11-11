"""The optional Puppet adapter uses Rigora without loading its former host."""
import builtins
from pathlib import Path
import tomllib

import pytest


def test_missing_rigora_reports_the_optional_install(monkeypatch):
    from frontengine.utils.imervue.runtime import puppet_runtime

    original = builtins.__import__

    def import_without_rigora(name, *args, **kwargs):
        if name == 'rigora' or name.startswith('rigora.'):
            raise ModuleNotFoundError("No module named 'rigora'", name='rigora')
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, '__import__', import_without_rigora)
    with pytest.raises(ValueError, match=r'Install Rigora GUI.*authorized local checkout or wheel'):
        puppet_runtime()


def test_installed_rigora_adapter_does_not_import_imervue(monkeypatch):
    pytest.importorskip('rigora.puppet.document_io')
    from frontengine.utils.imervue.runtime import puppet_runtime

    original = builtins.__import__

    def import_without_imervue(name, *args, **kwargs):
        if name == 'Imervue' or name.startswith('Imervue.'):
            pytest.fail(f'Legacy runtime dependency imported: {name}')
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, '__import__', import_without_imervue)
    runtime = puppet_runtime()
    assert runtime.Canvas.__module__ == 'rigora.puppet.canvas'
    assert runtime.load.__module__ == 'rigora.puppet.document_io'
    assert runtime.Script.__module__ == 'rigora.desktop_pet.pet_script'


@pytest.mark.parametrize('filename', ['pyproject.toml', 'stable.toml'])
def test_private_rigora_has_no_registry_extra(filename):
    root = Path(__file__).resolve().parents[2]
    metadata = tomllib.loads((root / filename).read_text(encoding='utf-8'))
    assert 'puppet' not in metadata['project']['optional-dependencies']
