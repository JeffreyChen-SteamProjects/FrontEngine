import threading

from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QColor, QImage

from frontengine.show.reference.image_compare import align_images, checked_image, difference_image
from frontengine.ui.dialog.image_compare_dialog import ImageCompareDialog, comparison_pool


def _image(width, height, color):
    image = QImage(width, height, QImage.Format.Format_RGBA8888)
    image.fill(QColor(color))
    return image


def test_different_sizes_have_explicit_origin_center_and_proportional_fit():
    a, b = _image(4, 2, 'red'), _image(2, 4, 'blue')
    first, second = align_images(a, b, 'origin')
    assert first.size() == second.size()
    assert (first.width(), first.height()) == (4, 4)
    assert first.pixelColor(0, 0) == QColor('red')
    assert first.pixelColor(0, 3).alpha() == 0
    first, second = align_images(a, b, 'center')
    assert first.pixelColor(0, 0).alpha() == 0
    assert first.pixelColor(0, 1) == QColor('red')
    assert second.pixelColor(1, 0) == QColor('blue')
    first, second = align_images(a, b, 'fit')
    assert first.size() == a.size() == second.size()
    assert second.pixelColor(0, 0).alpha() == 0
    assert second.pixelColor(1, 0) == QColor('blue')
    assert second.pixelColor(2, 0).alpha() == 0


def test_difference_uses_exact_rgb_without_unsigned_wrap_or_hidden_alpha_noise():
    diff = difference_image(_image(2, 1, '#ff0000'), _image(2, 1, '#0000ff'))
    assert diff.pixelColor(0, 0) == QColor('#ff00ff')
    transparent_a, transparent_b = _image(2, 1, '#ff0000'), _image(2, 1, '#0000ff')
    transparent_a.fill(QColor(255, 0, 0, 0))
    transparent_b.fill(QColor(0, 0, 255, 0))
    assert difference_image(transparent_a, transparent_b).pixelColor(0, 0) == QColor('black')


def test_reader_rejects_bad_data_and_limits_before_decode(tmp_path):
    import pytest
    from unittest.mock import patch
    from PySide6.QtCore import QSize
    good = tmp_path / 'good.png'
    _image(20, 30, 'red').save(str(good))
    assert checked_image(str(good)).height() == 30
    bad = tmp_path / 'bad.png'
    bad.write_bytes(b'not an image')
    with pytest.raises(ValueError):
        checked_image(str(bad))
    with patch('frontengine.show.reference.image_compare.QImageReader') as reader:
        reader.return_value.size.return_value = QSize(10000, 10000)
        with pytest.raises(ValueError, match='dimensions'):
            checked_image(str(good))
        reader.return_value.read.assert_not_called()


def _finish(dialog):
    assert comparison_pool().waitForDone(5000)
    QCoreApplication.processEvents()
    # An obsolete result may schedule the latest coalesced request.
    if dialog._busy:
        assert comparison_pool().waitForDone(5000)
        QCoreApplication.processEvents()
    assert not dialog._busy


def test_async_modes_share_transform_slider_avoids_decode_and_failure_keeps_pair(tmp_path, monkeypatch):
    import frontengine.ui.dialog.image_compare_dialog as module
    paths = [tmp_path / 'a.png', tmp_path / 'b.png']
    _image(10, 6, 'red').save(str(paths[0]))
    _image(6, 10, 'blue').save(str(paths[1]))
    gui_thread = threading.get_ident()
    calls = []
    original = module.checked_image

    def record(path):
        calls.append(threading.get_ident())
        return original(path)

    monkeypatch.setattr(module, 'checked_image', record)
    dialog = ImageCompareDialog()
    dialog.load_paths([str(path) for path in paths])
    _finish(dialog)
    assert len(calls) == 2 and all(identifier != gui_thread for identifier in calls)
    a, b, diff = dialog._items
    assert b.pos().x() == 34
    dialog.view.resetTransform()
    dialog.view.scale(2, 2)
    for mode in ('overlay', 'wipe', 'difference', 'side'):
        dialog.mode.setCurrentIndex(dialog.mode.findData(mode))
        assert dialog.view.transform().m11() == 2
    dialog.mode.setCurrentIndex(dialog.mode.findData('overlay'))
    dialog.amount.setValue(25)
    assert b.opacity() == 0.25
    dialog.mode.setCurrentIndex(dialog.mode.findData('wipe'))
    assert a.clip.width() == 2.5
    assert b.clip.x() == 2.5
    assert len(calls) == 2
    dialog.load_paths([str(paths[0]), str(tmp_path / 'missing.png')])
    _finish(dialog)
    assert dialog._items == [a, b, diff]
    dialog.close()
    assert not dialog.scene.items() and not dialog._items


def test_only_latest_pending_selection_is_applied_and_close_ignores_late_result(tmp_path):
    paths = [tmp_path / 'a.png', tmp_path / 'b.png']
    for path in paths:
        _image(12, 8, 'red').save(str(path))
    dialog = ImageCompareDialog()
    dialog.load_paths([str(path) for path in paths])
    dialog.alignment.setCurrentIndex(dialog.alignment.findData('center'))
    dialog.alignment.setCurrentIndex(dialog.alignment.findData('fit'))
    _finish(dialog)
    assert dialog._loaded_request[2] == 'fit'
    dialog.load_paths([str(path) for path in paths])
    dialog.close()
    _finish(dialog)
    assert dialog._closed and not dialog.scene.items()


def test_scene_output_matches_wipe_overlay_and_difference_controls():
    from PySide6.QtGui import QPainter
    dialog = ImageCompareDialog()
    request = ('a.png', 'b.png', 'origin', 1)
    dialog._request = request
    a, b = _image(4, 2, 'red'), _image(4, 2, 'blue')
    dialog._completed(request, (a, b, difference_image(a, b)), '')

    def render():
        result = _image(4, 2, 'white')
        painter = QPainter(result)
        dialog.scene.render(painter)
        painter.end()
        return result

    dialog.mode.setCurrentIndex(dialog.mode.findData('wipe'))
    result = render()
    assert result.pixelColor(0, 0) == QColor('red')
    assert result.pixelColor(3, 0) == QColor('blue')
    dialog.mode.setCurrentIndex(dialog.mode.findData('overlay'))
    dialog.amount.setValue(0)
    assert render().pixelColor(0, 0) == QColor('red')
    dialog.amount.setValue(100)
    assert render().pixelColor(0, 0) == QColor('blue')
    dialog.mode.setCurrentIndex(dialog.mode.findData('difference'))
    assert render().pixelColor(0, 0) == QColor('#ff00ff')
    dialog.close()


def test_closed_queued_job_skips_decode_and_pool_has_a_global_bound(monkeypatch):
    from threading import Event
    from unittest.mock import Mock
    import frontengine.ui.dialog.image_compare_dialog as module
    cancelled = Event()
    cancelled.set()
    decode = Mock()
    monkeypatch.setattr(module, 'checked_image', decode)
    module._CompareJob(('a', 'b', 'origin', 1), cancelled).run()
    decode.assert_not_called()
    assert comparison_pool().maxThreadCount() == 2
