"""Editable note text must remain visible under global rendering preferences."""
import pytest
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtTest import QTest

from frontengine.show.notes.sticky_note_widget import StickyNoteWidget


@pytest.mark.parametrize('backend', ['auto', 'gpu', 'software'])
def test_note_text_remains_visible_after_backend_change(backend):
    note = StickyNoteWidget('VISIBLE NOTE', width=320, height=180)
    try:
        note.show()
        note.set_render_backend(backend)
        note.set_text('EDITED NOTE')
        QTest.qWait(60)
        image = note.grab().toImage()
        dark_pixels = sum(
            image.pixelColor(x, y).lightness() < 100
            for x in range(10, image.width() - 10)
            for y in range(10, image.height() - 10)
        )
        assert note.text() == 'EDITED NOTE'
        assert dark_pixels > 20, f'Visible text pixels: {dark_pixels}'
    finally:
        note.close()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
