"""Create local native acceptance inputs; PyAV is required only to generate the silent video."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil
import wave


def make_video(path: Path) -> None:
    """Create a silent synthetic red video, never read host capture devices."""
    import av
    import numpy
    with av.open(str(path), 'w') as container:
        stream = container.add_stream('mpeg4', rate=10)
        stream.width, stream.height, stream.pix_fmt = 160, 90, 'yuv420p'
        for _ in range(30):
            data = numpy.zeros((90, 160, 3), dtype=numpy.uint8)
            data[:, :, 0] = 220
            for packet in stream.encode(av.VideoFrame.from_ndarray(data, format='rgb24')):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)


def make_fixtures(directory: Path, puppet: Path) -> None:
    """Write fixed fixture assets into a new directory and copy a selected puppet read-only."""
    import numpy
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QImage, QColor
    from frontengine.utils.recording.gif_writer import encode_gif
    directory.mkdir(parents=True, exist_ok=False)
    image = QImage(24, 24, QImage.Format.Format_RGB32)
    image.fill(QColor('blue'))
    assert image.save(str(directory / 'image.png'))
    frames = [numpy.full((32, 32, 3), color, dtype=numpy.uint8) for color in ([0, 255, 0], [255, 255, 0])]
    (directory / 'animation.gif').write_bytes(encode_gif(frames, delay_ms=100))
    make_video(directory / 'video.mp4')
    with wave.open(str(directory / 'sound.wav'), 'wb') as stream:
        stream.setparams((1, 2, 48000, 0, 'NONE', 'not compressed'))
        stream.writeframes(b'\0\0' * 48000)
    (directory / 'web.html').write_text('<body style="margin:0;background:#13579b;color:white"><input id="input" value="Local packaged preview"></body>', encoding='utf-8')
    shutil.copyfile(puppet, directory / 'character.puppet')
    entries = {
        'video': {'type':'VIDEO','file_path':'video.mp4','width':160,'height':90},
        'web': {'type':'WEB','url':QUrl.fromLocalFile(str(directory / 'web.html')).toString(),'x':160,'width':160,'height':90},
        'puppet': {'type':'PUPPET','file_path':'character.puppet','y':90,'width':240,'height':360},
        'image': {'type':'IMAGE','file_path':'image.png','width':24,'height':24,'z':20},
        'gif': {'type':'GIF','file_path':'animation.gif','x':250,'y':120,'width':32,'height':32},
        'text': {'type':'TEXT','text':'FrontEngine packaged preview','font_size':12,'x':250,'y':200,'width':180,'height':80},
        'sound': {'type':'SOUND','file_path':'sound.wav','x':250,'y':320,'width':160,'height':80}}
    for entry in entries.values():
        entry['opacity'] = 100
    (directory / 'scene.json').write_text(json.dumps(entries, indent=2), encoding='utf-8')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--puppet', type=Path, required=True)
    args = parser.parse_args()
    from PySide6.QtWidgets import QApplication
    application = QApplication([])
    make_fixtures(args.directory.resolve(), args.puppet.resolve())
    application.processEvents()


if __name__ == '__main__':
    main()
