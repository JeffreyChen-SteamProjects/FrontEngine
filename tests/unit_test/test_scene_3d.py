"""3D documents, portable assets and animation must work without a GL context."""
import json
from pathlib import Path

import numpy as np
import pytest

from frontengine.utils.scene_format.scene_3d_document import make_3d_scene, read_scene_document
from frontengine.utils.scene_format.scene_document import normalize_scene
from frontengine.utils.scene_format.scene_editor_document import SceneEditorDocument
from frontengine.utils.scene_format.scene_package import save_package, load_package
from frontengine.utils.scene_format.scene_source import read_scene_source
from frontengine.show.scene.math3d import interpolate, sample_entries, world_matrices, euler_quaternion
from frontengine.show.scene.model_asset import load_model, model_dependencies
from frontengine.show.scene.runtime3d import Scene3DClock, Scene3DRuntime
from frontengine.utils.scene_format.scene_3d_fixtures import model_fixture, obj_fixture


def test_v2_roundtrip_and_v1_compatibility():
    scene = make_3d_scene({'caption': {'type': 'TEXT', 'text': 'Hello', 'x': 12, 'z': 7}})
    assert scene == read_scene_document(scene.envelope())
    assert scene.entries['caption']['x'] == 12
    assert scene.entries['caption']['z'] == 7
    assert read_scene_document({'t': {'type': 'TEXT', 'text': 'old'}}).mode == '2d'
    with pytest.raises(ValueError, match='metadata'):
        normalize_scene(scene.envelope())


@pytest.mark.parametrize('mutation', [
    lambda d: d.update(camera='missing'),
    lambda d: d.update(canvas=[True, 1080]),
    lambda d: d.update(background=[0, 0]),
    lambda d: d.update(playback={'rate': float('nan')}),
    lambda d: d['entries']['camera'].update(transform={'rotation': [0, 0, 0, 0]}),
    lambda d: d['entries']['camera'].update(parent='camera'),
    lambda d: d['entries']['camera'].update(near=5, far=4),
    lambda d: d['entries']['camera'].update(tracks={'position': [{'time': 0, 'value': [0, 0, 0]}, {'time': 0, 'value': [1, 1, 1]}]}),
])
def test_v2_rejects_invalid_input_before_allocating(mutation):
    data = make_3d_scene().envelope()
    mutation(data)
    with pytest.raises(ValueError):
        read_scene_document(data)


def test_scene_settings_and_mode_have_atomic_undo():
    editor = SceneEditorDocument()
    editor.reset({'title': {'type': 'TEXT', 'text': 'old'}})
    editor.replace_document(make_3d_scene(editor.entries))
    camera = editor.scene.camera
    scene = editor.scene.copy()
    scene.playback = {'rate': 2, 'loop': True}
    editor.replace_document(scene)
    editor.undo.undo()
    assert editor.scene.camera == camera
    assert editor.scene.playback.get('rate', 1) == 1
    editor.undo.undo()
    assert editor.scene.mode == '2d'
    editor.undo.redo()
    assert editor.scene.mode == '3d'
    with pytest.raises(ValueError, match='camera'):
        editor.remove(camera)


def test_hierarchy_and_quaternion_animation():
    scene = make_3d_scene({'group': {'type': 'GROUP', 'transform': {'position': [1, 0, 0]}},
        'cube': {'type': 'CUBE', 'parent': 'group', 'transform': {'position': [0, 2, 0]},
                 'tracks': {'position': [{'time': 0, 'value': [0, 2, 0]}, {'time': 2, 'value': [2, 2, 0]}],
                            'rotation': [{'time': 0, 'value': [0, 0, 0, 1]}, {'time': 2, 'value': euler_quaternion([0, 90, 0])}]}}})
    entries = sample_entries(scene.entries, 1)
    assert np.allclose(world_matrices(entries)['cube'][:3, 3], [2, 2, 0])
    assert np.linalg.norm(entries['cube']['transform']['rotation']) == pytest.approx(1)
    assert np.allclose(interpolate(np.array([0., 1.]), np.array([[0.], [0.], [2.], [2.], [1.], [0.]]), .5, 'CUBICSPLINE'), [.5])
    scene.entries['group']['parent'] = 'cube'
    with pytest.raises(ValueError, match='cycle'):
        read_scene_document(scene)


def test_gltf_skin_morph_and_glb(tmp_path):
    path = model_fixture(tmp_path)
    asset = load_model(path)
    before = asset.sample(0, {'loop': False})[0][1]
    after = asset.sample(1, {'loop': False})[0][1]
    assert np.allclose(after-before, [[1, .5, 0]]*3)
    from pygltflib import GLTF2, BufferFormat
    gltf = GLTF2().load(str(path))
    with pytest.warns(UserWarning, match='orphaned'):
        gltf.convert_buffers(BufferFormat.BINARYBLOB)
    glb = tmp_path / 'triangle.glb'
    gltf.save_binary(str(glb))
    assert np.allclose(load_model(glb).sample(1, {'loop': False})[0][1], after)


def test_obj_material_and_package_dependencies(tmp_path):
    path = obj_fixture(tmp_path / 'models')
    asset = load_model(path)
    assert len(asset.sample()) == 1
    assert {p.suffix for p in model_dependencies(path)} == {'.obj', '.mtl'}
    scene = make_3d_scene({'model': {'type': 'MODEL', 'file_path': str(path)}})
    package = tmp_path / 'portable.fescene'
    save_package(scene, package)
    loaded, lease = load_package(package)
    try:
        assert loaded.mode == '3d'
        assert load_model(loaded.entries['model']['file_path']).sample()
        assert Path(loaded.entries['model']['file_path']).parent != path.parent
    finally:
        lease.cleanup()


def test_gltf_package_and_background_preparation(tmp_path):
    path = model_fixture(tmp_path / 'source')
    scene = make_3d_scene({'model': {'type': 'MODEL', 'file_path': str(path)}})
    target = tmp_path / 'scene.fescene'
    save_package(scene, target)
    prepared = read_scene_source(target)
    try:
        assert prepared.document.camera == scene.camera
        assert prepared.models
        assert prepared.entries == prepared.document.entries
    finally:
        prepared.close()


@pytest.mark.parametrize('uri', ['../outside.bin', 'https://example.test/geometry.bin', 'file:///outside.bin'])
def test_model_resource_resolver_rejects_escape_and_network(tmp_path, uri):
    path = model_fixture(tmp_path)
    data = json.loads(path.read_text())
    data['buffers'][0]['uri'] = uri
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        load_model(path)


def test_unsupported_required_extension_is_explicit(tmp_path):
    path = model_fixture(tmp_path)
    data = json.loads(path.read_text())
    data['extensionsRequired'] = ['KHR_draco_mesh_compression']
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='KHR_draco'):
        load_model(path)


def test_clock_pause_seek_rate_loop_and_hidden_views():
    now = [0.]
    clock = Scene3DClock(clock=lambda: now[0])
    clock.duration = 10
    clock.set_active(True)
    clock.play()
    now[0] = 2
    clock.tick()
    assert clock.position == 2
    clock.set_rate(2)
    now[0] = 3
    clock.tick()
    assert clock.position == 4
    clock.pause()
    now[0] = 100
    clock.tick()
    assert clock.position == 4
    clock.seek(9)
    clock.set_loop(True)
    clock.play()
    now[0] += 1
    clock.tick()
    assert clock.position == 1
    clock.set_active(False)
    now[0] += 100
    clock.set_active(True)
    clock.tick()
    assert clock.position == 1
    clock.shutdown()


def test_runtime_shares_pose_and_does_not_mutate_document():
    scene = make_3d_scene({'cube': {'type': 'CUBE', 'transform': {'position': [1, 2, 3]}}})
    before = scene.copy()
    runtime = Scene3DRuntime(scene, {})
    try:
        first = runtime.render_data()
        assert first['draws'][0]['key'] == 'cube'
        assert runtime.render_data()['draws'] is first['draws']
        runtime.set_owner('first', True)
        runtime.set_owner('second', True)
        runtime.set_owner('first', False)
        assert runtime.timeline.active
        runtime.set_owner('second', False)
        assert not runtime.timeline.active
        assert scene == before
    finally:
        runtime.close()
        runtime.close()


def test_primitive_winding_matches_normals():
    from frontengine.show.scene.math3d import primitive_mesh
    for kind in ('CUBE', 'SPHERE', 'PLANE'):
        positions, normals, _, indices = primitive_mesh(kind)
        triangle = indices.reshape(-1, 3)
        cross = np.cross(positions[triangle[:, 1]]-positions[triangle[:, 0]],
                         positions[triangle[:, 2]]-positions[triangle[:, 0]])
        facing = np.sum(cross*normals[triangle[:, 0]], axis=1)
        assert facing.min() >= -1e-6
        assert np.any(facing > 0)


def test_group_duplication_and_deletion_are_undoable():
    document = SceneEditorDocument()
    document.reset(make_3d_scene({'group': {'type': 'GROUP'}, 'child': {'type': 'CUBE', 'parent': 'group'}}))
    duplicate = document.duplicate('group')
    copied_children = [key for key, entry in document.entries.items() if entry.get('parent') == duplicate]
    assert len(copied_children) == 1
    document.remove(duplicate)
    assert copied_children[0] not in document.entries
    assert 'child' in document.entries
    document.undo.undo()
    assert document.entries[copied_children[0]]['parent'] == duplicate


def test_gif_seeks_by_real_frame_duration_and_stays_muted(tmp_path):
    from PIL import Image
    from frontengine.show.scene.runtime3d import prepare_models
    path = tmp_path / 'two.gif'
    Image.new('RGB', (16, 16), 'red').save(path, save_all=True,
        append_images=[Image.new('RGB', (16, 16), 'blue')], duration=[100, 300], loop=0)
    scene = make_3d_scene({'gif': {'type': 'GIF', 'file_path': str(path), 'width': 16, 'height': 16}})
    runtime = Scene3DRuntime(scene, prepare_models(scene), preview=True)
    try:
        runtime.timeline.seek(.15)
        assert runtime.sources['gif'].frame().pixelColor(0, 0).blue() == 255
        runtime.timeline.seek(.05)
        assert runtime.sources['gif'].frame().pixelColor(0, 0).red() == 255
        assert runtime.timeline.duration == pytest.approx(.4)
        assert runtime.muted
    finally:
        runtime.close()


def test_video_clock_sync_forces_seek_and_avoids_seeking_each_frame(monkeypatch, tmp_path):
    from frontengine.show.scene.runtime3d import MediaSource
    import frontengine.show.scene.media_frame as module
    calls = []
    class Player:
        position_value = 0
        def duration(self): return 10000
        def position(self): return self.position_value
        def isSeekable(self): return True
        def setPosition(self, value):
            self.position_value = value
            calls.append(('seek', value))
        def setPlaybackRate(self, value): calls.append(('rate', value))
    class Source:
        def __init__(self, *_args, **_kwargs): self.media_player = Player()
        def resize(self, *_args): pass
        def set_active(self, active): calls.append(('active', active))
        def set_muted(self, muted): calls.append(('muted', muted))
        def close(self): pass
        def deleteLater(self): pass
    monkeypatch.setattr(module, 'SceneMediaFrame', Source)
    source = MediaSource({'type': 'SOUND', 'file_path': str(tmp_path/'audio.wav'), 'play_rate': 200})
    try:
        source.sync(2, True, .5, False)
        assert ('seek', 4000) in calls and ('rate', 1) in calls
        calls.clear()
        source.sync(2.02, True, .5, False)
        assert not any(name == 'seek' for name, _ in calls)
        source.sync(2.02, False, .5, True, force=True)
        assert ('seek', 4040) in calls and ('muted', True) in calls
    finally:
        source.close()


def test_external_texture_survives_portable_package(tmp_path):
    from PIL import Image
    path = model_fixture(tmp_path/'source', animated=False)
    Image.new('RGB', (8, 8), 'blue').save(path.parent/'blue.png')
    data = json.loads(path.read_text())
    data['images'] = [{'uri': 'blue.png'}]
    data['textures'] = [{'source': 0}]
    data['materials'][0]['pbrMetallicRoughness']['baseColorTexture'] = {'index': 0}
    path.write_text(json.dumps(data))
    scene = make_3d_scene({'model': {'type': 'MODEL', 'file_path': str(path)}})
    save_package(scene, tmp_path/'portable.fescene')
    document, lease = load_package(tmp_path/'portable.fescene')
    try:
        asset = load_model(document.entries['model']['file_path'])
        image = asset.meshes[0][0].material.textures['base']['image']
        assert image.pixelColor(0, 0).blue() == 255
    finally:
        lease.cleanup()


def test_interleaved_and_sparse_accessor_decoding(tmp_path):
    from frontengine.show.scene.model_asset import GLTFReader
    path = model_fixture(tmp_path, animated=False)
    data = json.loads(path.read_text())
    blob = bytearray((path.parent/'geometry.bin').read_bytes())
    while len(blob) % 4: blob.append(0)
    start = len(blob)
    blob.extend(np.array([[1, 2, 3, 99], [4, 5, 6, 99]], '<f4').tobytes())
    data['bufferViews'].append({'buffer': 0, 'byteOffset': start, 'byteLength': 32, 'byteStride': 16})
    data['accessors'].append({'bufferView': len(data['bufferViews'])-1, 'componentType': 5126, 'count': 2, 'type': 'VEC3'})
    index = len(data['accessors'])-1
    ids_start = len(blob)
    blob.extend(b'\x01\x00\x00\x00')
    values_start = len(blob)
    blob.extend(np.array([7, 8, 9], '<f4').tobytes())
    data['bufferViews'] += [{'buffer': 0, 'byteOffset': ids_start, 'byteLength': 1},
                            {'buffer': 0, 'byteOffset': values_start, 'byteLength': 12}]
    data['accessors'].append({'componentType': 5126, 'count': 2, 'type': 'VEC3', 'sparse': {
        'count': 1, 'indices': {'bufferView': len(data['bufferViews'])-2, 'componentType': 5121},
        'values': {'bufferView': len(data['bufferViews'])-1}}})
    data['buffers'][0]['byteLength'] = len(blob)
    (path.parent/'geometry.bin').write_bytes(blob)
    path.write_text(json.dumps(data))
    reader = GLTFReader(path)
    assert np.allclose(reader.accessor(index), [[1, 2, 3], [4, 5, 6]])
    assert np.allclose(reader.accessor(index+1), [[0, 0, 0], [7, 8, 9]])


def test_extracted_assets_wait_for_all_background_readers():
    import tempfile
    from frontengine.utils.scene_format.scene_resource_reads import SceneResourceRead, release_scene_lease
    lease = tempfile.TemporaryDirectory(prefix='frontengine-reader-test-')
    root = Path(lease.name)
    asset = root/'asset.png'
    asset.write_bytes(b'owned fixture')
    scene = make_3d_scene({'image': {'type': 'IMAGE', 'file_path': str(asset)}})
    first, second = SceneResourceRead(scene), SceneResourceRead(scene)
    try:
        release_scene_lease(lease)
        assert asset.is_file()
        first.close()
        assert asset.is_file()
        second.close()
        assert not root.exists()
        second.close()
    finally:
        first.close()
        second.close()
        lease.cleanup()


@pytest.mark.parametrize('singular', [False, True])
def test_optimized_skinning_matches_inverse_transpose_for_scaled_bones(singular):
    from frontengine.show.scene.model_asset import ModelAsset, Mesh
    random = np.random.default_rng(3)
    positions = random.normal(size=(12, 3)).astype(np.float32)
    normals = random.normal(size=(12, 3)).astype(np.float32)
    mesh = Mesh(positions, normals, np.zeros((12, 2), np.float32), np.arange(12, dtype=np.uint32))
    mesh.joints = np.tile([0, 1, 0, 0], (12, 1))
    mesh.weights = np.tile([.5, .5, 0, 0], (12, 1)).astype(np.float32)
    first, second = np.eye(4), np.eye(4)
    if singular:
        second[1, 1] = second[2, 2] = -1
    else:
        first[:3, :3] = [[1, .2, 0], [0, 2, .1], [0, 0, .5]]
        second[:3, :3] = [[.5, 0, .1], [.1, 1, 0], [0, .2, 3]]
        second[:3, 3] = [1, 2, 3]
    asset = ModelAsset([[mesh]], [{'mesh': 0, 'skin': 0}, {'matrix': first.T.reshape(-1).tolist()},
        {'matrix': second.T.reshape(-1).tolist()}], [0, 1, 2],
        skins=[{'joints': [1, 2], 'inverse': [np.eye(4), np.eye(4)]}])
    _, actual_position, actual_normal, _ = asset.sample()[0]
    blended = (first+second)/2
    expected_position = (blended[:3, :3] @ positions.T).T+blended[:3, 3]
    expected_normal = (np.linalg.pinv(blended[:3, :3]).T @ normals.T).T
    assert np.allclose(actual_position, expected_position, atol=1e-6)
    assert np.allclose(actual_normal, expected_normal, atol=2e-6)
