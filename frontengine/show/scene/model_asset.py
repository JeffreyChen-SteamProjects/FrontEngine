"""Bounded, local-only glTF/GLB and OBJ preparation without OpenGL calls."""
from __future__ import annotations

import base64
from copy import deepcopy
from dataclasses import dataclass, field
from io import BytesIO
import json
from pathlib import Path
import shlex
from urllib.parse import unquote, urlsplit

import numpy as np
from PySide6.QtGui import QImage

from .math3d import interpolate, transform_matrix

MAX_MODEL_BYTES = 256 * 1024 * 1024
MAX_DECODED_BYTES = 512 * 1024 * 1024
COMPONENTS = {5120: 'i1', 5121: 'u1', 5122: '<i2', 5123: '<u2', 5125: '<u4', 5126: '<f4'}
WIDTHS = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT2': 4, 'MAT3': 9, 'MAT4': 16}


def local_resource(root, uri):
    if not isinstance(uri, str) or not uri or urlsplit(uri).scheme or urlsplit(uri).netloc:
        raise ValueError('Model resources must be local relative paths')
    path = Path(unquote(uri))
    if path.is_absolute():
        raise ValueError('Model resources must be relative to the model directory')
    target = (root / path).resolve()
    if not target.is_relative_to(root.resolve()) or not target.is_file():
        raise ValueError(f'Missing model resource or path outside model directory: {uri}')
    if target.stat().st_size > MAX_MODEL_BYTES:
        raise ValueError('Model resource exceeds 256 MiB')
    return target


def _gltf(path):
    from pygltflib import GLTF2
    if path.stat().st_size > MAX_MODEL_BYTES:
        raise ValueError('Model exceeds 256 MiB')
    try:
        model = GLTF2().load(str(path))
        data = json.loads(model.to_json())
    except (Exception,) as error:
        raise ValueError(f'Cannot read glTF: {error}') from error
    if data.get('asset', {}).get('version') != '2.0':
        raise ValueError('Only glTF 2.0 is supported')
    allowed = {'KHR_materials_unlit', 'KHR_texture_transform'}
    unsupported = set(data.get('extensionsRequired', [])) - allowed
    if unsupported:
        raise ValueError('Unsupported required glTF extensions: ' + ', '.join(sorted(unsupported)))
    return data, model.binary_blob()


def model_dependencies(path):
    """Return the complete local tree used by a model, preserving relative names."""
    path = Path(path).resolve()
    result = {path}
    if path.suffix.lower() in ('.glb', '.gltf'):
        data, _ = _gltf(path)
        for item in data.get('buffers', []) + data.get('images', []):
            uri = item.get('uri')
            if uri and not uri.startswith('data:'):
                result.add(local_resource(path.parent, uri))
    elif path.suffix.lower() == '.obj':
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            words = shlex.split(line, comments=True)
            if words and words[0] == 'mtllib':
                for name in words[1:]:
                    material = local_resource(path.parent, name)
                    result.add(material)
                    for row in material.read_text(encoding='utf-8-sig').splitlines():
                        tokens = shlex.split(row, comments=True)
                        if tokens and tokens[0].lower() in ('map_kd', 'map_ka', 'map_ks', 'map_d', 'map_bump', 'bump', 'norm'):
                            texture = local_resource(material.parent, tokens[-1])
                            if not texture.is_relative_to(path.parent):
                                raise ValueError('MTL texture is outside the model directory')
                            result.add(texture)
    else:
        raise ValueError('Choose a GLB, glTF or OBJ model')
    if sum(p.stat().st_size for p in result) > MAX_MODEL_BYTES:
        raise ValueError('Model resources exceed 256 MiB')
    return result


@dataclass
class Material:
    color: list = field(default_factory=lambda: [1, 1, 1, 1])
    metallic: float = 0.
    roughness: float = 1.
    emissive: list = field(default_factory=lambda: [0, 0, 0])
    textures: dict = field(default_factory=dict)
    alpha_mode: str = 'OPAQUE'
    cutoff: float = .5
    double_sided: bool = False
    unlit: bool = False


@dataclass
class Mesh:
    positions: np.ndarray
    normals: np.ndarray
    uv: np.ndarray
    indices: np.ndarray
    material: Material = field(default_factory=Material)
    uv1: np.ndarray | None = None
    colors: np.ndarray | None = None
    targets: list = field(default_factory=list)
    joints: np.ndarray | None = None
    weights: np.ndarray | None = None


def normals_for(positions, indices):
    normals = np.zeros_like(positions)
    triangles = indices.reshape(-1, 3)
    vectors = np.cross(positions[triangles[:, 1]]-positions[triangles[:, 0]],
                       positions[triangles[:, 2]]-positions[triangles[:, 0]])
    for column in range(3):
        np.add.at(normals, triangles[:, column], vectors)
    return normals / np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1e-12)


@dataclass
class ModelAsset:
    meshes: list
    nodes: list
    roots: list
    skins: list = field(default_factory=list)
    clips: list = field(default_factory=list)
    decoded_bytes: int = 0
    dependencies: set = field(default_factory=set)

    def sample(self, seconds=0, clip=None):
        nodes = deepcopy(self.nodes)
        clip = clip or {}
        if self.clips and seconds >= clip.get('start', 0):
            index = clip.get('index', 0)
            if index >= len(self.clips):
                raise ValueError('Model animation clip does not exist')
            animation = self.clips[index]
            stamp = (seconds-clip.get('start', 0))*clip.get('rate', 1)
            duration = animation['duration']
            stamp = stamp % duration if clip.get('loop', True) and duration > 0 else min(stamp, duration)
            for channel in animation['channels']:
                value = interpolate(channel['times'], channel['values'], stamp,
                                    channel['interpolation'], channel['path'] == 'rotation')
                nodes[channel['node']][channel['path']] = value
        matrices, visiting = {}, set()
        parents = {child: index for index, node in enumerate(nodes) for child in node.get('children', [])}
        def matrix(index):
            if index in visiting:
                raise ValueError('glTF node hierarchy contains a cycle')
            if index not in matrices:
                visiting.add(index)
                node = nodes[index]
                local = np.asarray(node['matrix']).reshape(4, 4).T if node.get('matrix') else transform_matrix({
                    'position': node.get('translation', [0, 0, 0]), 'rotation': node.get('rotation', [0, 0, 0, 1]),
                    'scale': node.get('scale', [1, 1, 1])})
                matrices[index] = matrix(parents[index]) @ local if index in parents else local
                visiting.remove(index)
            return matrices[index]
        draws = []
        visited = set()
        def visit(index):
            if index in visited:
                return
            visited.add(index)
            node = nodes[index]
            world = matrix(index)
            for source in self.meshes[node['mesh']] if 'mesh' in node else []:
                if abs(np.linalg.det(world[:3, :3])) < 1e-12:
                    continue
                position, normal = source.positions, source.normals
                if source.targets:
                    position, normal = position.copy(), normal.copy()
                    for weight, target in zip(node.get('weights', [0]*len(source.targets)), source.targets):
                        position += weight * target.get('POSITION', 0)
                        normal += weight * target.get('NORMAL', 0)
                if 'skin' in node and source.joints is not None:
                    skin = self.skins[node['skin']]
                    palette = np.asarray([np.linalg.inv(world) @ matrix(joint) @ inverse
                                          for joint, inverse in zip(skin['joints'], skin['inverse'])], dtype=np.float32)
                    if source.joints.max(initial=0) >= len(palette):
                        raise ValueError('Skin joint index is outside its palette')
                    # Accumulate one influence at a time instead of materializing
                    # an N×influences×4×4 array for every rendered frame.
                    blended = np.zeros((len(position), 4, 4), dtype=np.float32)
                    for influence in range(source.weights.shape[1]):
                        weights = source.weights[:, influence]
                        if np.any(weights):
                            blended += palette[source.joints[:, influence]]*weights[:, None, None]
                    position = np.einsum('nij,nj->ni', blended[:, :3, :3], position)+blended[:, :3, 3]
                    # Exact inverse-transpose via cofactors; use an SVD only for
                    # singular blended transforms, preserving nonuniform scales.
                    a, b, c = blended[:, :3, 0], blended[:, :3, 1], blended[:, :3, 2]
                    cofactor = np.cross(b, c)
                    determinant = np.einsum('ni,ni->n', a, cofactor)
                    transformed = (cofactor*normal[:, 0, None]+np.cross(c, a)*normal[:, 1, None]
                                   +np.cross(a, b)*normal[:, 2, None])
                    regular = np.abs(determinant) > 1e-8
                    transformed[regular] /= determinant[regular, None]
                    if not regular.all():
                        transformed[~regular] = np.einsum('nij,nj->ni',
                            np.linalg.pinv(blended[~regular, :3, :3]).transpose(0, 2, 1), normal[~regular])
                    normal = transformed
                draws.append((source, position.astype(np.float32, copy=False), normal.astype(np.float32, copy=False), world))
            for child in node.get('children', []):
                visit(child)
        for root in self.roots:
            visit(root)
        return draws


class GLTFReader:
    def __init__(self, path):
        self.path = Path(path).resolve()
        self.dependencies = model_dependencies(self.path)
        self.data, binary = _gltf(self.path)
        self.buffers, self.used, self.cache, self.images = [], 0, {}, {}
        for buffer in self.data.get('buffers', []):
            uri = buffer.get('uri')
            blob = self.uri(uri) if uri else binary
            if blob is None or len(blob) < buffer['byteLength']:
                raise ValueError('glTF buffer is truncated')
            self.buffers.append(blob)
            self.budget(len(blob))

    def budget(self, size):
        self.used += size
        if self.used > MAX_DECODED_BYTES:
            raise ValueError('Decoded model exceeds 512 MiB')

    def uri(self, uri):
        if uri.startswith('data:'):
            header, encoded = uri.split(',', 1)
            if ';base64' not in header or len(encoded) > MAX_MODEL_BYTES*4//3+4:
                raise ValueError('Invalid or oversized embedded model resource')
            return base64.b64decode(encoded, validate=True)
        return local_resource(self.path.parent, uri).read_bytes()

    def view(self, index):
        view = self.data['bufferViews'][index]
        buffer = self.buffers[view['buffer']]
        start, size = view.get('byteOffset', 0), view['byteLength']
        if start < 0 or size < 0 or start+size > len(buffer):
            raise ValueError('glTF buffer view is out of bounds')
        return memoryview(buffer)[start:start+size], view

    def accessor(self, index):
        if index in self.cache:
            return self.cache[index]
        accessor = self.data['accessors'][index]
        dtype = np.dtype(COMPONENTS[accessor['componentType']])
        width, count = WIDTHS[accessor['type']], accessor['count']
        if count < 0 or count*width*dtype.itemsize > MAX_DECODED_BYTES:
            raise ValueError('glTF accessor exceeds the decoded resource budget')
        self.budget(count*width*max(dtype.itemsize, 4))
        if 'bufferView' in accessor:
            blob, view = self.view(accessor['bufferView'])
            start, stride = accessor.get('byteOffset', 0), view.get('byteStride', width*dtype.itemsize)
            if stride < width*dtype.itemsize or start < 0 or (count and start+(count-1)*stride+width*dtype.itemsize > len(blob)):
                raise ValueError('glTF accessor is out of bounds')
            result = np.ndarray((count, width), dtype, blob, start, (stride, dtype.itemsize)).copy()
        else:
            result = np.zeros((count, width), dtype)
        if accessor.get('sparse'):
            sparse = accessor['sparse']
            length = sparse['count']
            indices, _ = self.view(sparse['indices']['bufferView'])
            values, _ = self.view(sparse['values']['bufferView'])
            idtype = np.dtype(COMPONENTS[sparse['indices']['componentType']])
            ids = np.frombuffer(indices, idtype, length, sparse['indices'].get('byteOffset', 0))
            if length > count or np.any(ids >= count) or len(np.unique(ids)) != length:
                raise ValueError('Invalid sparse accessor indices')
            result[ids] = np.frombuffer(values, dtype, length*width, sparse['values'].get('byteOffset', 0)).reshape(length, width)
        if accessor.get('normalized') and dtype.kind in ('i', 'u'):
            result = np.maximum(-1, result.astype(np.float32)/np.iinfo(dtype).max)
        if not np.isfinite(result).all():
            raise ValueError('Model contains nonfinite vertex or animation data')
        self.cache[index] = result
        return result

    def texture(self, info):
        texture = self.data['textures'][info['index']]
        index = texture['source']
        if index not in self.images:
            item = self.data['images'][index]
            blob = self.uri(item['uri']) if item.get('uri') else bytes(self.view(item['bufferView'])[0])
            from PIL import Image
            with Image.open(BytesIO(blob)) as image:
                if max(image.size) > 8192 or image.width*image.height > 16_777_216:
                    raise ValueError('Model texture exceeds 8192 pixels or 16 megapixels')
                self.budget(image.width*image.height*4)
                raw = image.convert('RGBA').tobytes()
                self.images[index] = QImage(raw, image.width, image.height, QImage.Format.Format_RGBA8888).copy()
        sampler = self.data.get('samplers', [])[texture['sampler']] if 'sampler' in texture else {}
        transform = info.get('extensions', {}).get('KHR_texture_transform', {})
        uv = transform.get('texCoord', info.get('texCoord', 0))
        if uv not in (0, 1):
            raise ValueError('Only texture coordinate sets 0 and 1 are supported')
        return {'image': self.images[index], 'uv': uv, 'sampler': sampler, 'transform': transform,
                'strength': info.get('strength', info.get('scale', 1))}

    def material(self, index):
        if index is None:
            return Material(metallic=1)
        data = self.data['materials'][index]
        pbr = data.get('pbrMetallicRoughness', {})
        textures = {}
        for key, info in (('base', pbr.get('baseColorTexture')), ('metal', pbr.get('metallicRoughnessTexture')),
                          ('normal', data.get('normalTexture')), ('occlusion', data.get('occlusionTexture')),
                          ('emissive', data.get('emissiveTexture'))):
            if info:
                textures[key] = self.texture(info)
        return Material(pbr.get('baseColorFactor', [1, 1, 1, 1]), pbr.get('metallicFactor', 1),
                        pbr.get('roughnessFactor', 1), data.get('emissiveFactor', [0, 0, 0]), textures,
                        data.get('alphaMode', 'OPAQUE'), data.get('alphaCutoff', .5),
                        data.get('doubleSided', False), 'KHR_materials_unlit' in data.get('extensions', {}))

    def load(self):
        meshes = []
        for group in self.data.get('meshes', []):
            primitives = []
            for primitive in group['primitives']:
                if primitive.get('mode', 4) not in (4, 5, 6):
                    raise ValueError('Only triangle glTF primitives are supported')
                attributes = primitive['attributes']
                positions = self.accessor(attributes['POSITION']).astype(np.float32)
                indices = self.accessor(primitive['indices']).reshape(-1) if 'indices' in primitive else np.arange(len(positions))
                if indices.dtype.kind not in ('i', 'u') or np.any(indices < 0) or np.any(indices >= len(positions)):
                    raise ValueError('Triangle indices are outside their vertex buffer')
                mode = primitive.get('mode', 4)
                if mode in (5, 6):
                    indices = np.asarray([(indices[i], indices[i+1], indices[i+2]) if i % 2 == 0 else
                                          (indices[i+1], indices[i], indices[i+2]) for i in range(len(indices)-2)]) if mode == 5 else np.asarray(
                                          [(indices[0], indices[i], indices[i+1]) for i in range(1, len(indices)-1)])
                indices = indices.astype(np.uint32).reshape(-1)
                if len(indices) % 3 or positions.shape[1] != 3:
                    raise ValueError('Invalid triangle mesh')
                def attribute(name, default):
                    value = self.accessor(attributes[name]).astype(np.float32) if name in attributes else default
                    if len(value) != len(positions):
                        raise ValueError('Mismatched vertex attribute counts')
                    return value
                normals = attribute('NORMAL', np.empty((len(positions), 3), np.float32)) if 'NORMAL' in attributes else normals_for(positions, indices)
                uv = attribute('TEXCOORD_0', np.zeros((len(positions), 2), np.float32))
                uv1 = attribute('TEXCOORD_1', uv)
                color = attribute('COLOR_0', np.ones((len(positions), 4), np.float32))
                if color.shape[1] == 3:
                    color = np.column_stack([color, np.ones(len(color))])
                if normals.shape != positions.shape or uv.shape != (len(positions), 2) or uv1.shape != uv.shape or color.shape != (len(positions), 4):
                    raise ValueError('Invalid vertex attribute dimensions')
                mesh = Mesh(positions, normals, uv, indices, self.material(primitive.get('material')), uv1, color)
                for target in primitive.get('targets', []):
                    values = {name: self.accessor(index).astype(np.float32) for name, index in target.items() if name in ('POSITION', 'NORMAL')}
                    if any(value.shape != positions.shape for value in values.values()):
                        raise ValueError('Invalid morph target dimensions')
                    mesh.targets.append(values)
                if 'JOINTS_0' in attributes:
                    mesh.joints = self.accessor(attributes['JOINTS_0']).astype(np.int32)
                    mesh.weights = attribute('WEIGHTS_0', None)
                    if 'JOINTS_1' in attributes:
                        mesh.joints = np.column_stack([mesh.joints, self.accessor(attributes['JOINTS_1']).astype(np.int32)])
                        mesh.weights = np.column_stack([mesh.weights, attribute('WEIGHTS_1', None)])
                    if np.any(mesh.joints < 0) or np.any(mesh.weights < 0):
                        raise ValueError('Invalid skin influences')
                    mesh.weights /= np.maximum(mesh.weights.sum(axis=1, keepdims=True), 1e-12)
                primitives.append(mesh)
            meshes.append(primitives)
        nodes = deepcopy(self.data.get('nodes', []))
        children = set()
        for node in nodes:
            for child in node.get('children', []):
                if type(child) is not int or not 0 <= child < len(nodes) or child in children:
                    raise ValueError('Invalid or multiply parented glTF node')
                children.add(child)
            for name, width in (('matrix', 16), ('translation', 3), ('rotation', 4), ('scale', 3)):
                if name in node and (np.asarray(node[name]).shape != (width,) or not np.isfinite(node[name]).all()):
                    raise ValueError('Invalid model node transform')
            if 'mesh' in node and 'weights' not in node:
                node['weights'] = self.data['meshes'][node['mesh']].get('weights', [0]*len(meshes[node['mesh']][0].targets))
        skins = []
        for skin in self.data.get('skins', []):
            inverse = self.accessor(skin['inverseBindMatrices']).reshape(-1, 4, 4).transpose(0, 2, 1) if 'inverseBindMatrices' in skin else np.tile(np.eye(4), (len(skin['joints']), 1, 1))
            if len(inverse) != len(skin['joints']):
                raise ValueError('Skin inverse matrix count is invalid')
            skins.append({'joints': skin['joints'], 'inverse': inverse})
        clips = []
        for animation in self.data.get('animations', []):
            channels, duration = [], 0.
            for channel in animation['channels']:
                target, sampler = channel['target'], animation['samplers'][channel['sampler']]
                if target.get('node') is None:
                    continue
                kind = target['path']
                if kind not in ('translation', 'rotation', 'scale', 'weights'):
                    raise ValueError('Unsupported glTF animation target')
                times = self.accessor(sampler['input']).reshape(-1)
                values = self.accessor(sampler['output'])
                interpolation = sampler.get('interpolation', 'LINEAR')
                if interpolation not in ('LINEAR', 'STEP', 'CUBICSPLINE') or not len(times) or np.any(np.diff(times) <= 0) or times[0] < 0:
                    raise ValueError('Invalid glTF animation sampler')
                count = len(times)*(3 if interpolation == 'CUBICSPLINE' else 1)
                values = values.reshape(count, -1)
                duration = max(duration, float(times[-1]))
                channels.append({'node': target['node'], 'path': kind, 'times': times,
                                 'values': values, 'interpolation': interpolation})
            clips.append({'name': animation.get('name', f'Animation {len(clips)+1}'), 'channels': channels, 'duration': duration})
        scenes = self.data.get('scenes', [])
        roots = scenes[self.data.get('scene', 0)].get('nodes', []) if scenes else [i for i in range(len(nodes)) if not any(i in n.get('children', []) for n in nodes)]
        result = ModelAsset(meshes, nodes, roots, skins, clips, self.used, self.dependencies)
        result.sample()
        return result


def load_model(path):
    path = Path(path).resolve()
    try:
        if path.suffix.lower() in ('.gltf', '.glb'):
            return GLTFReader(path).load()
        dependencies = model_dependencies(path)
        import trimesh
        class LocalResolver(trimesh.resolvers.Resolver):
            def __init__(self, root=path.parent):
                self.root = root
            def get(self, name):
                return local_resource(self.root, name).read_bytes()
            def namespaced(self, namespace):
                root = (self.root / namespace).resolve()
                if not root.is_relative_to(path.parent):
                    raise ValueError('OBJ resource namespace is outside model directory')
                return LocalResolver(root)
            def keys(self):
                return [p.relative_to(path.parent).as_posix() for p in dependencies]
            def write(self, name, data):
                raise ValueError('Model loading cannot write resources')
        with path.open('rb') as stream:
            scene = trimesh.load_scene(stream, file_type='obj', resolver=LocalResolver(), maintain_order=True,
                                       split_objects=True, split_groups=True, process=False)
        if isinstance(scene, trimesh.Trimesh):
            scene = trimesh.Scene(scene)
        meshes, nodes, used = [], [], 0
        for name in scene.graph.nodes_geometry:
            matrix, geometry = scene.graph[name]
            geometry = scene.geometry[geometry]
            positions, indices = np.asarray(geometry.vertices, np.float32), np.asarray(geometry.faces, np.uint32).reshape(-1)
            used += positions.nbytes*4+indices.nbytes
            if used > MAX_DECODED_BYTES:
                raise ValueError('Decoded OBJ exceeds 512 MiB')
            material, uv = Material(), np.zeros((len(positions), 2), np.float32)
            if hasattr(geometry.visual, 'uv') and geometry.visual.uv is not None:
                uv = np.asarray(geometry.visual.uv, np.float32)
                uv[:, 1] = 1-uv[:, 1]
            source = getattr(geometry.visual, 'material', None)
            if source is not None:
                material.color = (np.asarray(source.diffuse)/255).tolist()
                if source.image is not None:
                    image = source.image.convert('RGBA')
                    if image.width*image.height > 16_777_216 or max(image.size) > 8192:
                        raise ValueError('OBJ texture exceeds the resource limit')
                    used += image.width*image.height*4
                    material.textures['base'] = {'image': QImage(image.tobytes(), image.width, image.height, QImage.Format.Format_RGBA8888).copy(),
                                                 'uv': 0, 'sampler': {}, 'transform': {}}
                if material.color[3] < 1:
                    material.alpha_mode = 'BLEND'
            mesh = Mesh(positions, np.asarray(geometry.vertex_normals, np.float32), uv, indices, material)
            meshes.append([mesh])
            nodes.append({'mesh': len(meshes)-1, 'matrix': matrix.T.reshape(-1).tolist()})
        if not meshes:
            raise ValueError('Model has no triangle geometry')
        return ModelAsset(meshes, nodes, list(range(len(nodes))), decoded_bytes=used, dependencies=dependencies)
    except (ValueError, OSError):
        raise
    except Exception as error:
        raise ValueError(f'Invalid model {path.name}: {error}') from error
