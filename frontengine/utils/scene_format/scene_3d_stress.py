"""Load, animate and dispose large original meshes through the production renderer."""
from pathlib import Path
import time
import statistics

from frontengine.show.scene.runtime3d import Scene3DRuntime, prepare_models
from frontengine.show.scene.view3d import OffscreenScene3D
from .scene_3d_document import make_3d_scene
from .scene_3d_fixtures import model_fixture


def verify_stress(directory, vertices):
    results = {}
    for animated in (False, True):
        name = 'skin_morph' if animated else 'static'
        path = model_fixture(Path(directory)/name, animated=animated, vertex_count=vertices)
        document = make_3d_scene({'model': {'type': 'MODEL', 'file_path': str(path),
                                          **({'clip': {'loop': False}} if animated else {})}})
        document.entries[document.camera]['transform']['position'] = [0, 0, 5]
        document.playback['duration'] = 1
        runtime = surface = None
        try:
            start = time.perf_counter()
            assets = prepare_models(document)
            asset = assets[str(path.resolve())]
            elapsed_load = time.perf_counter()-start
            runtime = Scene3DRuntime(document, assets, preview=True)
            surface = OffscreenScene3D(runtime, (640, 480))
            durations, first, last = [], None, None
            for step in range(8):
                runtime.timeline.seek(step/7)
                start = time.perf_counter()
                image = surface.frame()
                durations.append((time.perf_counter()-start)*1000)
                if first is None:
                    first = image
                last = image
                if image.isNull():
                    raise RuntimeError(f'Large {name} mesh produced an empty frame')
            if animated and first == last:
                raise RuntimeError('Large skin/morph scene did not animate')
            results[name] = {'vertices': sum(len(mesh.positions) for group in asset.meshes for mesh in group),
                             'triangles': sum(len(mesh.indices)//3 for group in asset.meshes for mesh in group),
                             'load_seconds': round(elapsed_load, 3), 'decoded_bytes': asset.decoded_bytes,
                             'gpu_bytes': surface.renderer._gpu_bytes,
                             'median_frame_ms': round(statistics.median(durations), 3),
                             'max_frame_ms': round(max(durations), 3)}
        finally:
            if surface:
                renderer = surface.renderer
                surface.close()
                if renderer._gpu_bytes or renderer.meshes or renderer.textures:
                    raise RuntimeError('Large model GPU resources were retained after close')
            if runtime:
                runtime.close()
                if runtime.sources or runtime.models or runtime.meshes or runtime.timeline.timer.isActive():
                    raise RuntimeError('Large model runtime resources were retained after close')
    return results
