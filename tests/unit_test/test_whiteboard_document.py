"""Editable multi-page persistence, pan/zoom selection and bounded exports."""
from copy import deepcopy
import math
import threading
import time

import pytest
from PySide6.QtCore import QPoint, Qt, QEvent, QCoreApplication, QThreadPool
from PySide6.QtGui import QImage
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from frontengine.utils.whiteboard.document import WhiteboardDocument, read_document, write_document, normalize_document
from frontengine.utils.whiteboard.raster import render_page, save_page
from frontengine.show.canvas.whiteboard_widget import WhiteboardWidget, to_screen


def line(color='#ff0000'):
    return {'color': color, 'width': 4, 'points': [[20, 200], [120, 200]]}


def wait(predicate):
    deadline = time.monotonic() + 5
    while not predicate() and time.monotonic() < deadline:
        QApplication.processEvents()
        threading.Event().wait(.005)
    assert predicate()


def test_document_reopens_all_pages_and_remains_editable(tmp_path):
    document = WhiteboardDocument()
    document.page.update(strokes=[line()], zoom=2, offset=[40, 60])
    document.add_page()
    document.page['strokes'] = [line('#0000ff')]
    path = tmp_path / 'board.fewhiteboard'
    write_document(document.snapshot(), str(path))
    reopened = WhiteboardDocument()
    reopened.replace(read_document(str(path)))
    assert reopened.current == 1 and len(reopened.pages) == 2
    assert reopened.pages[0]['zoom'] == 2 and reopened.pages[0]['offset'] == [40, 60]
    reopened.checkpoint()
    reopened.page['strokes'][0]['points'][0][0] += 50
    assert reopened.undo() and reopened.page['strokes'][0]['points'][0] == [20, 200]
    assert document.page['strokes'][0]['points'][0] == [20, 200]
    assert write_document(reopened.snapshot(), str(path)) == str(path)


@pytest.mark.parametrize('change', [
    lambda value: value.update(version=2),
    lambda value: value.update(current=True),
    lambda value: value.update(pages=[]),
    lambda value: value['pages'][0].update(zoom=math.nan),
    lambda value: value['pages'][0].update(offset=[0]),
    lambda value: value['pages'][0].update(strokes=[{'points': [[0, 0]], 'width': 4, 'color': '#ff0000'}]),
    lambda value: value['pages'][0].update(strokes=[dict(line(), color='red')]),
    lambda value: value['pages'][0].update(strokes=[dict(line(), width=65)]),
])
def test_bad_document_never_replaces_existing_pages(change):
    document = WhiteboardDocument()
    document.page['strokes'] = [line()]
    before = document.snapshot()
    value = deepcopy(before)
    change(value)
    with pytest.raises(ValueError):
        document.replace(value)
    assert document.snapshot() == before


def test_atomic_cancellation_and_bounds_keep_existing_file(tmp_path):
    path = tmp_path / 'keep.fewhiteboard'
    path.write_text('sentinel')
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(InterruptedError):
        write_document(WhiteboardDocument().snapshot(), str(path), cancel=cancel)
    assert path.read_text() == 'sentinel'
    document = WhiteboardDocument()
    for _index in range(49):
        document.add_page()
    with pytest.raises(ValueError):
        document.add_page()
    value = document.snapshot()
    value['pages'][0]['strokes'] = [dict(line(), points=[[0, 0]] * 100001)]
    with pytest.raises(ValueError, match='100000'):
        normalize_document(value)
    for _index in range(50):
        document.remove_page()
    assert len(document.pages) == 1 and document.current == 0


def test_active_page_pixels_exclude_view_and_other_pages_and_wide_pens(tmp_path):
    document = WhiteboardDocument()
    document.page['strokes'] = [dict(line(), width=64)]
    before = render_page(document.page)
    document.page.update(zoom=3, offset=[100, -20])
    assert render_page(document.page) == before
    assert before.pixelColor(0, 0).alpha() == 0
    assert before.pixelColor(56, 56).red() > 200
    assert before.pixelColor(56, 23).alpha() == 0
    assert before.pixelColor(56, 24).alpha() == 255  # Full pen width has transparent margin.
    document.add_page()
    document.page['strokes'] = [line('#0000ff')]
    path = tmp_path / 'page.png'
    save_page(document.page, str(path))
    assert QImage(str(path)).pixelColor(26, 26).blue() > 200
    document.page['strokes'][0]['points'][1][0] = 100000
    with pytest.raises(ValueError, match='8192'):
        save_page(document.page, str(path))
    assert QImage(str(path)).pixelColor(26, 26).blue() > 200


def test_zoomed_selection_move_delete_undo_and_page_switch():
    board = WhiteboardWidget()
    try:
        board.strokes = [line(), line('#0000ff')]
        board.zoom, board.offset = 2, [30, 40]
        point = QPoint(*map(int, to_screen((70, 200), board.offset, board.zoom)))
        assert board.select_at(point) == 1 and board.selected == {1}
        board.document.checkpoint()
        board.move_selected(40, 20)
        assert board.strokes[1]['points'][0] == (40, 210)
        assert board.strokes[0]['points'][0] == [20, 200]
        board.delete_selected()
        assert len(board.strokes) == 1
        assert board.undo() and len(board.strokes) == 2
        assert board.undo() and board.strokes[1]['points'][0] == [20, 200]
        board.add_page()
        assert board.strokes == [] and board.zoom == 1
        board.select_page(0)
        assert board.zoom == 2 and board.offset == [30, 40] and board.selected == set()
    finally:
        board.close()


def test_native_style_mouse_move_uses_canvas_delta_and_escape_releases_controls():
    board = WhiteboardWidget()
    try:
        board.resize(1000, 600)
        board.strokes = [line()]
        board.zoom = 2
        board.show()
        QApplication.processEvents()
        board.set_select_mode(True)
        QTest.mousePress(board, Qt.MouseButton.LeftButton, pos=QPoint(100, 400))
        QTest.mouseMove(board, QPoint(140, 440))
        QTest.mouseRelease(board, Qt.MouseButton.LeftButton, pos=QPoint(140, 440))
        assert board.strokes[0]['points'][0] == (40, 220)
        assert board.undo() and board.strokes[0]['points'][0] == [20, 200]
        QTest.keyClick(board, Qt.Key.Key_Escape)
        assert board.controls.closed
    finally:
        board.close()
        QCoreApplication.sendPostedEvents(board, QEvent.Type.DeferredDelete)


def test_file_worker_error_keeps_page_and_close_cancels(tmp_path):
    board = WhiteboardWidget()
    entered, release = threading.Event(), threading.Event()
    try:
        board.strokes = [line()]
        def invalid():
            raise ValueError('invalid file')
        board.controls._start('open', invalid)
        wait(lambda: board.controls.pending is None)
        assert board.strokes == [line()] and board.controls.status.text() == 'invalid file'
        def blocked():
            entered.set()
            assert release.wait(5)
            return WhiteboardDocument().snapshot()
        board.controls._start('open', blocked)
        wait(entered.is_set)
        cancel = board.controls.pending
        board.close()
        assert cancel.is_set() and board.controls.closed
        release.set()
        wait(lambda: board.controls.pending is None)
        assert board.strokes == [line()]
    finally:
        release.set()
        QThreadPool.globalInstance().waitForDone(5000)
        board.close()
