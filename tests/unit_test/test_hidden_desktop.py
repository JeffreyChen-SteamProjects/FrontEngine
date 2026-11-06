import subprocess
import sys
import json
from pathlib import Path

import pytest


pytestmark = pytest.mark.skipif(sys.platform != 'win32', reason='Requires Windows desktops')


def _probe(tmp_path):
    script = tmp_path / 'probe.py'
    script.write_text('''
import sys, uuid
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from tests.integration import hidden_desktop
output = Path(sys.argv[2])
if hidden_desktop.is_child(output if sys.argv[3] == 'output' else None):
    (output / 'entered-body').write_text('entered', encoding='utf-8')
else:
    hidden_desktop.DESKTOP = 'FrontEngineGuardTest' + uuid.uuid4().hex
    raise SystemExit(hidden_desktop.run_on_hidden_desktop(
        __file__, sys.argv[1], sys.argv[2], sys.argv[3], timeout_ms=0xFFFFFFFF))
''', encoding='utf-8')
    return [sys.executable, str(script), str(Path(__file__).resolve().parents[2]), str(tmp_path)]


@pytest.mark.parametrize('output', ['output', 'no-output'])
def test_input_desktop_cannot_enter_probe_body(tmp_path, output):
    result = subprocess.run([*_probe(tmp_path), output, '--child'], capture_output=True, text=True, timeout=60)
    assert result.returncode != 0
    assert not (tmp_path / 'entered-body').exists()
    error = (tmp_path / 'stderr.txt').read_text(encoding='utf-8') if output == 'output' else result.stderr
    assert 'input desktop' in error
    if output == 'output':
        desktops = json.loads((tmp_path / 'desktop.json').read_text(encoding='utf-8'))
        assert desktops['thread_desktop'] == desktops['input_desktop']


def test_private_desktop_can_enter_probe_body(tmp_path):
    result = subprocess.run([*_probe(tmp_path), 'output'], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    assert (tmp_path / 'entered-body').read_text(encoding='utf-8') == 'entered'
    assert not (tmp_path / 'stderr.txt').read_text(encoding='utf-8')
    desktops = json.loads((tmp_path / 'desktop.json').read_text(encoding='utf-8'))
    assert desktops['thread_desktop'].startswith('FrontEngineGuardTest')
    assert desktops['thread_desktop'] != desktops['input_desktop']
