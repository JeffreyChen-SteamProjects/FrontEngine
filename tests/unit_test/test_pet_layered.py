"""Layer compatibility and actual composed pixels, without native windows."""
import copy
import json

import pytest
from PySide6.QtGui import QColor, QImage

from frontengine.show.pet.layered_renderer import LayeredRenderer
from frontengine.utils.pet_pack.layered import load_layered_asset, validate_outfit


def make_asset(root, *, garment=False):
    root.mkdir()
    image = QImage(2, 2, QImage.Format.Format_ARGB32)
    image.fill(QColor('red' if garment else 'blue'))
    assert image.save(str(root / 'layer.png'))
    frames = [{'duration_ms': duration, 'anchors': {'head': [offset, 2]},
               'layers': [{'image': 'layer.png', 'z': 10 if garment else 0,
                           'anchor': 'head', 'offset': [0, 0]}]}
              for duration, offset in ((100, 2), (200, 6))]
    data = {'format': 'frontengine.layered-pet/1', 'id': root.name, 'version': '1',
            'name': root.name, 'kind': 'garment' if garment else 'character',
            'template': 'chibi-cat', 'canvas': [16, 16], 'slots': ['head'] if garment else [],
            'actions': {'idle': {'loop': True, 'frames': frames}}, 'license': 'test fixture'}
    write(root, data)
    return data


def write(root, data):
    (root / 'layered-pet.json').write_text(json.dumps(data), encoding='utf-8')


def test_shared_clock_anchors_mirroring_and_detached_cache(tmp_path):
    base, hat = tmp_path / 'cat', tmp_path / 'hat'
    make_asset(base)
    make_asset(hat, garment=True)
    renderer = LayeredRenderer(load_layered_asset(base), (load_layered_asset(hat),))
    first = renderer.render('idle', 99)
    assert first.pixelColor(2, 2) == QColor('red')
    assert first.pixelColor(6, 2).alpha() == 0
    next_frame = renderer.render('idle', 100)
    assert next_frame.pixelColor(6, 2) == QColor('red')
    assert next_frame.pixelColor(2, 2).alpha() == 0
    assert renderer.render('idle', 300) == first
    assert renderer.render('missing-interaction', 99) == first
    assert renderer.render('idle', 99, mirrored=True).pixelColor(13, 2) == QColor('red')
    first.fill(QColor('green'))
    assert renderer.render('idle', 99).pixelColor(2, 2) == QColor('red')


def test_back_layer_and_nonlooping_animation(tmp_path):
    base, hat = tmp_path / 'cat', tmp_path / 'hat'
    body = make_asset(base)
    garment = make_asset(hat, garment=True)
    for data in (body, garment):
        data['actions']['idle']['loop'] = False
    for frame in garment['actions']['idle']['frames']:
        frame['layers'][0]['z'] = -1
    write(base, body)
    write(hat, garment)
    renderer = LayeredRenderer(load_layered_asset(base), (load_layered_asset(hat),))
    assert renderer.render('idle', 100000).pixelColor(6, 2) == QColor('blue')


@pytest.mark.parametrize('change', ['template', 'canvas', 'timing', 'missing', 'anchor', 'slots'])
def test_incompatible_outfits_rejected_before_render(tmp_path, change):
    base, hat = tmp_path / 'cat', tmp_path / 'hat'
    make_asset(base)
    data = make_asset(hat, garment=True)
    if change in ('template', 'canvas'):
        data[change] = 'rabbit' if change == 'template' else [32, 32]
    elif change == 'timing':
        data['actions']['idle']['frames'][0]['duration_ms'] = 101
    elif change == 'missing':
        data['actions']['walk'] = data['actions'].pop('idle')
    elif change == 'anchor':
        data['actions']['idle']['frames'][0]['layers'][0]['anchor'] = 'missing'
    write(hat, data)
    garment = load_layered_asset(hat)
    with pytest.raises(ValueError):
        validate_outfit(load_layered_asset(base), (garment, garment) if change == 'slots' else (garment,))


@pytest.mark.parametrize('path', ['../outside.png', '/outside.png', 'C:/outside.png',
                                   'dir\\outside.png', 'dir/../layer.png'])
def test_asset_paths_cannot_escape_folder(tmp_path, path):
    base = tmp_path / 'cat'
    data = make_asset(base)
    data['actions']['idle']['frames'][0]['layers'][0]['image'] = path
    write(base, data)
    with pytest.raises(ValueError):
        load_layered_asset(base)


def test_frame_limits_invalid_duration_and_corrupt_image(tmp_path):
    base = tmp_path / 'cat'
    original = make_asset(base)
    for duration in (True, 0, 10001):
        data = copy.deepcopy(original)
        data['actions']['idle']['frames'][0]['duration_ms'] = duration
        write(base, data)
        with pytest.raises(ValueError):
            load_layered_asset(base)
    data = copy.deepcopy(original)
    data['actions']['idle']['frames'] *= 61
    write(base, data)
    with pytest.raises(ValueError):
        load_layered_asset(base)
    write(base, original)
    (base / 'layer.png').write_bytes(b'not PNG')
    with pytest.raises(ValueError):
        LayeredRenderer(load_layered_asset(base))


def test_high_resolution_authoring_canvas_retains_upper_bound(tmp_path):
    base = tmp_path / 'cat'
    data = make_asset(base)
    data['canvas'] = [2048, 2048]
    write(base, data)
    assert load_layered_asset(base).canvas == (2048, 2048)
    data['canvas'] = [2049, 2048]
    write(base, data)
    with pytest.raises(ValueError):
        load_layered_asset(base)
