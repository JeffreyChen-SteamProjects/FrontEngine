"""Tiny original geometry for CPU and real desktop GL acceptance tests."""
import json
from pathlib import Path

import numpy as np


def model_fixture(directory, *, animated=True, vertex_count=3):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    blob, views, accessors = bytearray(), [], []
    def accessor(values, kind, component=5126):
        data = np.asarray(values, {5126: '<f4', 5123: '<u2', 5125: '<u4'}[component])
        while len(blob) % 4:
            blob.append(0)
        views.append({'buffer': 0, 'byteOffset': len(blob), 'byteLength': data.nbytes})
        blob.extend(data.tobytes())
        accessors.append({'bufferView': len(views)-1, 'componentType': component,
                          'count': len(data), 'type': kind})
        return len(accessors)-1
    if vertex_count <= 3:
        positions, coordinates, faces = [[-1, -1, 0], [1, -1, 0], [0, 1, 0]], [[0, 1], [1, 1], [.5, 0]], [0, 1, 2]
    else:
        side = int(np.sqrt(vertex_count))
        x, y = np.meshgrid(np.linspace(-1, 1, side), np.linspace(-1, 1, side))
        positions = np.column_stack([x.reshape(-1), y.reshape(-1), np.zeros(side*side)])
        coordinates = np.column_stack([(x.reshape(-1)+1)/2, (1-y.reshape(-1))/2])
        base = (np.arange(side-1)[:, None]*side+np.arange(side-1)[None, :]).reshape(-1)
        faces = np.column_stack([base, base+1, base+side, base+1, base+side+1, base+side]).reshape(-1)
    count = len(positions)
    position = accessor(positions, 'VEC3')
    normal = accessor(np.tile([0, 0, 1], (count, 1)), 'VEC3')
    uv = accessor(coordinates, 'VEC2')
    indices = accessor(faces, 'SCALAR', 5123 if count <= 65535 else 5125)
    attributes = {'POSITION': position, 'NORMAL': normal, 'TEXCOORD_0': uv}
    primitive = {'attributes': attributes, 'indices': indices, 'material': 0}
    data = {'asset': {'version': '2.0'}, 'scene': 0, 'scenes': [{'nodes': [0]}],
            'nodes': [{'mesh': 0, 'name': 'Triangle'}], 'meshes': [{'primitives': [primitive]}],
            'materials': [{'pbrMetallicRoughness': {'baseColorFactor': [1, .1, .05, 1], 'metallicFactor': 0, 'roughnessFactor': .8}, 'doubleSided': True}]}
    if animated:
        attributes['JOINTS_0'] = accessor(np.zeros((count, 4)), 'VEC4', 5123)
        attributes['WEIGHTS_0'] = accessor(np.tile([1, 0, 0, 0], (count, 1)), 'VEC4')
        primitive['targets'] = [{'POSITION': accessor(np.tile([0, .5, 0], (count, 1)), 'VEC3')}]
        data['meshes'][0]['weights'] = [0]
        data['nodes'][0]['skin'] = 0
        data['nodes'].append({'name': 'Joint'})
        data['scenes'][0]['nodes'].append(1)
        inverse = accessor([np.eye(4).reshape(-1)], 'MAT4')
        data['skins'] = [{'joints': [1], 'inverseBindMatrices': inverse}]
        times = accessor([0, 1], 'SCALAR')
        translation = accessor([[0, 0, 0], [1, 0, 0]], 'VEC3')
        weights = accessor([0, 1], 'SCALAR')
        data['animations'] = [{'name': 'Move and morph', 'samplers': [
            {'input': times, 'output': translation}, {'input': times, 'output': weights}],
            'channels': [{'sampler': 0, 'target': {'node': 1, 'path': 'translation'}},
                         {'sampler': 1, 'target': {'node': 0, 'path': 'weights'}}]}]
    data.update(buffers=[{'uri': 'geometry.bin', 'byteLength': len(blob)}], bufferViews=views, accessors=accessors)
    (directory / 'geometry.bin').write_bytes(blob)
    target = directory / 'triangle.gltf'
    target.write_text(json.dumps(data), encoding='utf-8')
    return target


def obj_fixture(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'triangle.mtl').write_text('newmtl red\nKd 1 0 0\nd 1\n', encoding='utf-8')
    target = directory / 'triangle.obj'
    target.write_text('mtllib triangle.mtl\no triangle\nv -1 -1 0\nv 1 -1 0\nv 0 1 0\nvt 0 0\nvt 1 0\nvt .5 1\nusemtl red\nf 1/1 2/2 3/3\n', encoding='utf-8')
    return target
