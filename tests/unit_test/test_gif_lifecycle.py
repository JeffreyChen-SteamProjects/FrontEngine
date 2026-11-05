"""Closing an animation releases its source independently of Python references."""
import sys

from PIL import Image
from PySide6.QtCore import QCoreApplication, QEvent
import pytest
from shiboken6 import isValid

from frontengine.show.gif.paint_gif import GifWidget


@pytest.mark.skipif(sys.platform != 'win32', reason='Windows file sharing detects an open movie source')
def test_closing_gif_releases_source_while_python_references_remain(tmp_path):
    source = tmp_path / 'moving.gif'
    frames = [Image.new('RGB', (16, 16), color) for color in ('red', 'green')]
    frames[0].save(source, save_all=True, append_images=frames[1:], duration=100, loop=0)
    widget = GifWidget(str(source))
    movie = widget.movie
    try:
        assert movie.jumpToFrame(0)
        assert not movie.currentImage().isNull()
        widget.close()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        source.unlink()
        assert not source.exists()
    finally:
        if isValid(movie):
            movie.stop()
            movie.setFileName('')
        if isValid(widget):
            widget.close()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
