"""Generated sprite sheets become aligned transparent frames; only an undressed default pet uses them."""
import numpy
import pytest
from PySide6.QtGui import QColor, QImage, QPainter

from frontengine.show.pet.inkside.sprite_sheet import SPRITES, atlas_frame, cut_frames, fit_frames, key_magenta


def _sheet() -> QImage:
    """Two magenta cells, each with a dark figure standing at a different height."""
    sheet = QImage(200, 100, QImage.Format.Format_ARGB32)
    sheet.fill(QColor('#ff00ff'))
    painter = QPainter(sheet)
    painter.fillRect(30, 20, 40, 60, QColor('#202020'))
    painter.fillRect(130, 30, 40, 66, QColor('#202020'))
    painter.end()
    return sheet


def test_magenta_is_keyed_out_and_edges_are_unblended():
    pixels = numpy.array([[[255, 0, 255, 255], [32, 32, 32, 255], [143, 16, 143, 255]]], dtype=numpy.float32)
    out = key_magenta(pixels)
    assert out[0, 0, 3] == 0
    assert out[0, 1, 3] == 255 and tuple(out[0, 1, :3]) == (32, 32, 32)
    # Half dark, half magenta: partly transparent and no longer pink.
    assert 0 < out[0, 2, 3] < 255
    assert abs(out[0, 2, 0] - out[0, 2, 1]) < 40


def test_frames_share_one_scale_and_stand_on_the_ground_line():
    frames = fit_frames(cut_frames(_sheet(), 2, 1), canvas=128, height=100, ground=120, centre=64)
    for frame in frames:
        assert frame.size().width() == 128
        alpha = numpy.array([[frame.pixelColor(x, y).alpha() for x in range(128)] for y in range(128)])
        rows = numpy.nonzero(alpha.max(axis=1) > 128)[0]
        columns = numpy.nonzero(alpha.max(axis=0) > 128)[0]
        assert rows[-1] in (118, 119)
        assert abs((columns[0] + columns[-1]) / 2 - 64) <= 2
    heights = [numpy.count_nonzero([f.pixelColor(64, y).alpha() > 128 for y in range(128)]) for f in frames]
    assert heights[1] > heights[0]


@pytest.mark.parametrize('atlas', [f'inkside-{name}-{kind}.png' for name in ('mochi', 'moss', 'pip', 'bolt', 'ink', 'gill')
                                   for kind in ('walk', 'climb')])
def test_shipped_atlases_have_eight_distinct_frames(atlas):
    assert (SPRITES / atlas).is_file()
    frames = [atlas_frame(atlas, index) for index in range(8)]
    assert len({bytes(frame.constBits()) for frame in frames}) == 8


def test_wall_alignment_puts_the_combined_reach_on_the_wall():
    frames = fit_frames(cut_frames(_sheet(), 2, 1), canvas=128, height=100, ground=120, wall=110)
    rightmost = max(x for frame in frames for x in range(128) for y in range(0, 128, 4)
                    if frame.pixelColor(x, y).alpha() > 128)
    assert rightmost in (108, 109)
