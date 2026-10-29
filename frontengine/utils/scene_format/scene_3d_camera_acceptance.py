"""Send synthetic GPU output through the actual OBS driver and read it back via DirectShow."""
from pathlib import Path
import tempfile
from threading import Thread
import time

import numpy as np
from PySide6.QtGui import QImage, QPainter, QColor
from PySide6.QtWidgets import QApplication

from frontengine.show.scene.runtime3d import Scene3DRuntime, prepare_models
from frontengine.show.scene.view3d import OffscreenScene3D
from frontengine.utils.scene_format.scene_3d_document import make_3d_scene
from frontengine.utils.virtual_camera.frame_sender import FrameSender
from frontengine.utils.recording.frame_recorder import image_to_rgb


def verify_camera():
    import av
    if 'dshow' not in av.formats_available:
        raise RuntimeError('Actual camera readback requires the Windows DirectShow backend')
    app = QApplication.instance()
    errors, ready, captures = [], [], []
    sender = FrameSender(640, 480, 20)
    sender.failed.connect(errors.append)
    sender.ready.connect(ready.append)
    consumer = None
    runtime = surface = None
    with tempfile.TemporaryDirectory(prefix='frontengine-camera-fixture-') as directory:
        try:
            marker = QImage(64, 64, QImage.Format.Format_RGBA8888)
            marker.fill(QColor('red'))
            path = Path(directory)/'marker.png'
            if not marker.save(str(path)):
                raise RuntimeError('Cannot save virtual camera fixture')
            document = make_3d_scene({'cube': {'type': 'CUBE', 'color': [1, 0, 0],
                'transform': {'scale': [2, 2, 2]}}, 'marker': {'type': 'IMAGE', 'file_path': str(path),
                'x': 8, 'y': 8, 'width': 64, 'height': 64, 'opacity': 100}})
            document.canvas = (640, 480)
            document.entries[document.camera]['transform']['position'] = [0, 0, 5]
            runtime = Scene3DRuntime(document, prepare_models(document), preview=True)
            surface = OffscreenScene3D(runtime, (640, 480))
            sender.start()
            deadline = time.monotonic()+10
            while not ready and not errors and time.monotonic() < deadline:
                app.processEvents()
                time.sleep(.01)
            if errors or not ready:
                raise RuntimeError('; '.join(errors) or 'Virtual camera startup timed out')
            # OBS publishes its capture format after receiving the first frame.
            # Prime the real producer before DirectShow negotiates the output pin.
            initial = image_to_rgb(surface.frame())
            for _ in range(5):
                sender.submit(initial)
                app.processEvents()
                time.sleep(.05)

            def receive():
                seen, cube_seen, background_seen, count = set(), False, False, 0
                phase = 'open'
                try:
                    with av.open('video='+ready[0], format='dshow', options={'video_size': '640x480'},
                                 timeout=(5, 5)) as capture:
                        phase = 'decode'
                        for frame in capture.decode(video=0):
                            pixels = frame.to_ndarray(format='rgb24')
                            count += 1
                            patch = pixels[24:40, 24:40].mean(axis=(0, 1))
                            channel = int(np.argmax(patch))
                            if patch[channel] > 150 and np.max(np.delete(patch, channel)) < 80:
                                seen.add(channel)
                            center = pixels[232:248, 312:328].mean(axis=(0, 1))
                            cube_seen |= center[0] > 60 and max(center[1:]) < 35
                            background = pixels[440:456, 600:616].mean(axis=(0, 1))
                            background_seen |= np.max(np.abs(background-[18, 52, 86])) < 20
                            if len(seen) == 3 and cube_seen and background_seen:
                                captures.append({'read_frames': count, 'marker_colors': 3, 'cube_pixels': True,
                                                 'background_pixels': True, 'size': [pixels.shape[1], pixels.shape[0]]})
                                return
                            if time.monotonic() >= deadline+3:
                                break
                    errors.append(f'Camera readback did not match the scene: colors={seen}, cube={cube_seen}, background={background_seen}')
                except Exception as error:
                    errors.append(f'{phase}: {error}')

            consumer = Thread(target=receive, daemon=True)
            consumer.start()
            deadline = time.monotonic()+10
            index = 0
            while not captures and not errors and time.monotonic() < deadline:
                marker = QImage(64, 64, QImage.Format.Format_RGBA8888)
                marker.fill(QColor(('red', 'lime', 'blue')[(index//6) % 3]))
                runtime.sources['marker'].image = marker
                runtime.timeline.seek(index/20)
                image = surface.frame()
                opaque = QImage(image.size(), QImage.Format.Format_RGB32)
                opaque.fill(QColor('#123456'))
                painter = QPainter(opaque)
                painter.drawImage(0, 0, image)
                painter.end()
                sender.submit(image_to_rgb(opaque))
                app.processEvents()
                index += 1
                time.sleep(.05)
            if errors or not captures:
                raise RuntimeError('; '.join(errors) or 'Virtual camera readback timed out')
            return {'device': ready[0], 'sent_frames': sender.frames, **captures[0]}
        finally:
            if consumer is not None:
                consumer.join(4)
            sender.stop()
            if sender.thread.ident is not None:
                sender.thread.join(5)
                if sender.thread.is_alive():
                    raise RuntimeError('Virtual camera sender did not release the real device')
            if consumer is not None and consumer.is_alive():
                raise RuntimeError('Virtual camera readback did not shut down')
            if surface:
                surface.close()
            if runtime:
                runtime.close()
