"""Verify the seven existing media types inside the actual 3D rendering pipeline."""
from pathlib import Path
import time

from PySide6.QtCore import QUrl, QEvent
from PySide6.QtWidgets import QApplication

from .scene_3d_document import make_3d_scene, MEDIA_TYPES
from .scene_source import read_scene_source
from frontengine.show.scene.runtime3d import Scene3DRuntime, prepare_models
from frontengine.show.scene.view3d import OffscreenScene3D


def verify_media(directory):
    directory = Path(directory).resolve()
    prepared = read_scene_source(directory/'scene.json')
    runtime = surface = None
    errors = []
    app = QApplication.instance()
    try:
        entries = prepared.entries
        if len(entries) != 7 or {entry.get('type') for entry in entries.values()} != MEDIA_TYPES:
            raise ValueError('Media acceptance requires exactly one of each of the seven media types')
        for entry in entries.values():
            if entry.get('script_path'):
                raise ValueError('Media acceptance fixtures cannot execute scripts')
            if entry['type'] == 'WEB':
                url = QUrl(entry.get('url', ''))
                if not url.isLocalFile() or not Path(url.toLocalFile()).resolve().is_relative_to(directory):
                    raise ValueError('Media acceptance requires a local web fixture')
            elif entry.get('file_path') and not Path(entry['file_path']).resolve().is_relative_to(directory):
                raise ValueError('Media acceptance assets must remain within the fixture directory')
        document = make_3d_scene(entries)
        document.canvas = (480, 480)
        document.playback['loop'] = True  # Loading native sources must not race the short fixture duration.
        runtime = Scene3DRuntime(document, prepare_models(document), preview=True)
        runtime.failed.connect(errors.append)
        surface = OffscreenScene3D(runtime, (480, 480))
        runtime.set_owner('acceptance', True)
        runtime.timeline.play()

        def wait_for(predicate):
            deadline = time.monotonic()+25
            while time.monotonic() < deadline:
                app.processEvents()
                if errors:
                    raise RuntimeError('; '.join(errors))
                surface.frame()
                if predicate():
                    return
                time.sleep(.01)
            states = {key: {'active': getattr(source.widget, 'active', None),
                            'frame_null': source.frame().isNull(), 'duration': source.duration}
                      for key, source in runtime.sources.items()}
            raise RuntimeError(f'Native 3D media acceptance timed out: {runtime.timeline.state}, {states}')

        def ready(source):
            kind = source.entry['type']
            if kind == 'SOUND':
                return source.widget.media_player.duration() > 0
            frame = source.frame()
            if frame.isNull():
                return False
            if kind == 'WEB':
                return frame.pixelColor(70, 40).name() == '#13579b'
            if kind == 'VIDEO':
                return frame.pixelColor(70, 40).red() > 190
            return True

        wait_for(lambda: all(ready(source) for source in runtime.sources.values()))
        image = surface.frame()
        if image.pixelColor(3, 3).blue() < 240 or image.pixelColor(70, 40).red() < 190 or image.pixelColor(230, 40).name() != '#13579b':
            pixels = [image.pixelColor(x, y).name() for x, y in ((3, 3), (70, 40), (230, 40))]
            raise RuntimeError(f'3D screen-space media composition differs from the existing scene layout: {pixels}')
        puppet = next(source for source in runtime.sources.values() if source.entry['type'] == 'PUPPET')
        if not puppet.widget.host.canvas.isValid() or not any(bytes(puppet.frame().constBits())[3::4]):
            raise RuntimeError('Puppet did not render through its native OpenGL framebuffer')
        if not all(source.widget.audio_output.isMuted() for source in runtime.sources.values()
                   if source.widget is not None and getattr(source.widget, 'audio_output', None) is not None):
            raise RuntimeError('3D media preview played audio unexpectedly')
        runtime.timeline.pause()
        runtime.timeline.seek(.7)
        video = next(source for source in runtime.sources.values() if source.entry['type'] == 'VIDEO')
        wait_for(lambda: abs(video.widget.sink.videoFrame().startTime()/1000000-.7) <= .2)
        video.frame()
        if video._video_stamp != (video.widget.sink.videoFrame().startTime(), video.widget.sink.videoFrame().endTime()):
            raise RuntimeError('Paused seeking did not update the video texture')
        gif = next(source for source in runtime.sources.values() if source.entry['type'] == 'GIF')
        runtime.timeline.seek(0)
        first = gif.frame().copy()
        runtime.timeline.seek(gif.durations[0]+.001)
        if first == gif.frame():
            raise RuntimeError('GIF did not follow scene seeking')
        return {'types': sorted(MEDIA_TYPES), 'image_video_web_pixels': True, 'puppet_native_fbo': True,
                'muted_preview': True, 'paused_video_seek': True, 'gif_seek': True}
    finally:
        if surface:
            surface.close()
        if runtime:
            runtime.close()
        QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        QApplication.processEvents()
        prepared.close()
