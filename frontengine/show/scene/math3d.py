"""CPU scene transforms and deterministic animation sampling (no GL context)."""
from __future__ import annotations

from copy import deepcopy
import math
import numpy as np


def quaternion(value):
    q = np.asarray(value, dtype=np.float64)
    length = np.linalg.norm(q)
    if length < 1e-12:
        return np.array([0., 0., 0., 1.])
    return q / length


def quaternion_product(left, right):
    a, b = quaternion(left), quaternion(right)
    vector = a[3]*b[:3]+b[3]*a[:3]+np.cross(a[:3], b[:3])
    return quaternion([*vector, a[3]*b[3]-np.dot(a[:3], b[:3])])


def slerp(left, right, ratio):
    a, b = quaternion(left), quaternion(right)
    dot = np.dot(a, b)
    if dot < 0:
        b, dot = -b, -dot
    if dot > .9995:
        return quaternion(a + (b - a) * ratio)
    angle = math.acos(np.clip(dot, -1, 1))
    return (a * math.sin((1 - ratio) * angle) + b * math.sin(ratio * angle)) / math.sin(angle)


def euler_quaternion(degrees):
    x, y, z = np.radians(degrees) / 2
    cx, cy, cz, sx, sy, sz = math.cos(x), math.cos(y), math.cos(z), math.sin(x), math.sin(y), math.sin(z)
    return quaternion([sx*cy*cz-cx*sy*sz, cx*sy*cz+sx*cy*sz,
                       cx*cy*sz-sx*sy*cz, cx*cy*cz+sx*sy*sz]).tolist()


def quaternion_euler(q):
    x, y, z, w = quaternion(q)
    return np.degrees([math.atan2(2*(w*x+y*z), 1-2*(x*x+y*y)),
                       math.asin(np.clip(2*(w*y-z*x), -1, 1)),
                       math.atan2(2*(w*z+x*y), 1-2*(y*y+z*z))]).tolist()


def transform_matrix(transform):
    x, y, z, w = quaternion(transform.get('rotation', [0, 0, 0, 1]))
    result = np.eye(4)
    result[:3, :3] = [[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                       [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                       [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]]
    result[:3, :3] *= np.asarray(transform.get('scale', [1, 1, 1]))
    result[:3, 3] = transform.get('position', [0, 0, 0])
    return result


def projection(camera, aspect):
    near, far = camera.get('near', .01), camera.get('far', 1000)
    result = np.zeros((4, 4))
    if camera.get('projection') == 'orthographic':
        height = camera.get('ortho_height', 10.8)
        result[0, 0], result[1, 1] = 2/(height*aspect), 2/height
        result[2, 2], result[2, 3], result[3, 3] = -2/(far-near), -(far+near)/(far-near), 1
    else:
        factor = 1 / math.tan(math.radians(camera.get('fov', 45)) / 2)
        result[0, 0], result[1, 1] = factor/aspect, factor
        result[2, 2], result[2, 3], result[3, 2] = (far+near)/(near-far), 2*far*near/(near-far), -1
    return result


def interpolate(times, values, seconds, interpolation='LINEAR', rotation=False):
    """glTF cubic outputs contain incoming tangent, value, outgoing tangent."""
    if not len(times):
        raise ValueError('Animation sampler is empty')
    cubic = interpolation == 'CUBICSPLINE'
    def at(index):
        return values[index * 3 + 1] if cubic else values[index]
    if seconds <= times[0]:
        return at(0).copy()
    if seconds >= times[-1]:
        return at(len(times)-1).copy()
    index = int(np.searchsorted(times, seconds, side='right')) - 1
    delta = times[index+1] - times[index]
    t = (seconds-times[index]) / delta
    if interpolation == 'STEP':
        return at(index).copy()
    if cubic:
        result = ((2*t**3-3*t*t+1)*at(index) + (t**3-2*t*t+t)*delta*values[index*3+2]
                  + (-2*t**3+3*t*t)*at(index+1) + (t**3-t*t)*delta*values[(index+1)*3])
        return quaternion(result) if rotation else result
    return slerp(at(index), at(index+1), t) if rotation else at(index)*(1-t)+at(index+1)*t


def sample_entries(entries, seconds):
    result = deepcopy(entries)
    from frontengine.utils.scene_format.scene_animation import sample_animation
    for entry in result.values():
        if entry.get('animation'):
            entry.update(sample_animation(entry, seconds))
        for channel, frames in entry.get('tracks', {}).items():
            times = np.asarray([frame['time'] for frame in frames])
            values = np.asarray([frame['value'] for frame in frames])
            index = min(len(frames)-1, int(np.searchsorted(times, seconds, side='left')))
            easing = frames[index].get('easing', 'linear')
            stamp = seconds
            if easing == 'smooth' and index > 0 and times[index-1] < seconds < times[index]:
                t = (seconds-times[index-1])/(times[index]-times[index-1])
                stamp = times[index-1] + t*t*(3-2*t)*(times[index]-times[index-1])
            value = interpolate(times, values, stamp, 'STEP' if easing == 'step' else 'LINEAR',
                                rotation=channel == 'rotation')
            if channel in ('position', 'rotation', 'scale3d'):
                entry.setdefault('transform', {})['scale' if channel == 'scale3d' else channel] = value.tolist()
            else:
                entry[channel] = value.tolist() if np.ndim(value) else float(value)
    return result


def world_matrices(entries):
    result = {}
    def visit(key):
        if key not in result:
            entry = entries[key]
            local = transform_matrix(entry.get('transform', {}))
            result[key] = visit(entry['parent']) @ local if entry.get('parent') else local
        return result[key]
    for key in entries:
        visit(key)
    return result


def primitive_mesh(kind):
    """Return indexed positions, normals and UV coordinates."""
    if kind == 'SPHERE':
        vertices, normals, uv, indices = [], [], [], []
        for row in range(17):
            phi = math.pi*row/16
            for column in range(25):
                theta = 2*math.pi*column/24
                normal = [math.sin(phi)*math.cos(theta), math.cos(phi), math.sin(phi)*math.sin(theta)]
                vertices.append(np.asarray(normal)*.5)
                normals.append(normal)
                uv.append([column/24, row/16])
        for row in range(16):
            for col in range(24):
                a = row*25+col
                indices.extend([a, a+1, a+25, a+1, a+26, a+25])
    else:
        vertices, normals, uv, indices = [], [], [], []
        faces = [(np.array([0, 0, 1]), np.array([1, 0, 0]), np.array([0, 1, 0]))]
        if kind == 'CUBE':
            faces += [(np.array(n), np.array(u), np.array(v)) for n, u, v in (
                ([0, 0, -1], [-1, 0, 0], [0, 1, 0]), ([1, 0, 0], [0, 0, -1], [0, 1, 0]),
                ([-1, 0, 0], [0, 0, 1], [0, 1, 0]), ([0, 1, 0], [1, 0, 0], [0, 0, -1]),
                ([0, -1, 0], [1, 0, 0], [0, 0, 1]))]
        for normal, u, v in faces:
            offset = len(vertices)
            for x, y, s, t in ((-.5, -.5, 0, 1), (.5, -.5, 1, 1), (.5, .5, 1, 0), (-.5, .5, 0, 0)):
                vertices.append(u*x+v*y+(normal*.5 if kind == 'CUBE' else 0))
                normals.append(normal)
                uv.append([s, t])
            indices.extend([offset, offset+1, offset+2, offset, offset+2, offset+3])
    return (np.asarray(vertices, np.float32), np.asarray(normals, np.float32),
            np.asarray(uv, np.float32), np.asarray(indices, np.uint32))
