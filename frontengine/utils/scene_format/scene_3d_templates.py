"""Original, asset-free examples that can be edited and shared immediately."""
from dataclasses import dataclass

from .scene_3d_document import make_3d_scene
from frontengine.show.scene.math3d import euler_quaternion


@dataclass(frozen=True)
class Scene3DTemplate:
    identifier: str
    title_key: str
    description_key: str

    def entries(self, translate):
        if self.identifier == '3d-media':
            return make_3d_scene({'title': {'type': 'TEXT', 'text': translate('scene3d_template_media'),
                'space': 'world', 'font_size': 48, 'width': 640, 'height': 180,
                'transform': {'position': [0, 0, 0], 'rotation': euler_quaternion([0, -20, 0])}},
                'sphere': {'type': 'SPHERE', 'color': [.1, .5, 1],
                           'transform': {'position': [0, -1.8, -1], 'scale': [2, 2, 2]}}})
        scene = make_3d_scene({'model_stage': {'type': 'GROUP'},
            'cube': {'type': 'CUBE', 'parent': 'model_stage', 'color': [.1, .55, 1],
                     'transform': {'scale': [2, 2, 2]}, 'tracks': {'rotation': [
                         {'time': 0, 'value': euler_quaternion([15, 0, 0])},
                         {'time': 3, 'value': euler_quaternion([15, 120, 0])},
                         {'time': 6, 'value': euler_quaternion([15, 240, 0])},
                         {'time': 9, 'value': euler_quaternion([15, 360, 0])}]}},
            'floor': {'type': 'PLANE', 'color': [.2, .22, .28], 'transform': {
                'position': [0, -1.2, 0], 'rotation': euler_quaternion([-90, 0, 0]), 'scale': [8, 8, 1]}}})
        scene.playback['loop'] = True
        if self.identifier == '3d-camera':
            scene.entries[scene.camera]['tracks'] = {'position': [
                {'time': 0, 'value': [-2, 0, 13]}, {'time': 4, 'value': [2, 0, 9], 'easing': 'smooth'},
                {'time': 8, 'value': [-2, 0, 13], 'easing': 'smooth'}]}
        return scene


BUILTIN_3D_TEMPLATES = (
    Scene3DTemplate('3d-media', 'scene3d_template_media', 'scene3d_template_media_hint'),
    Scene3DTemplate('3d-model', 'scene3d_template_model', 'scene3d_template_model_hint'),
    Scene3DTemplate('3d-camera', 'scene3d_template_camera', 'scene3d_template_camera_hint'),
)
