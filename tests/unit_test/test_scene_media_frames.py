"""Media ownership, frame delivery and preview lifecycle without devices/network."""
import pytest
from PySide6.QtCore import QObject, Signal, QUrl
from PySide6.QtGui import QColor, QImage
from PySide6.QtMultimedia import QVideoFrame
from PySide6.QtWidgets import QApplication, QWidget

from frontengine.show.scene.media_frame import SceneMediaFrame
from frontengine.ui.page.scene_setting.scene_media_preview import SceneMediaPreview


class Player(QObject):
    positionChanged = Signal(int)
    errorOccurred = Signal(int, str)

    def __init__(self, parent):
        super().__init__(parent)
        self.calls = []

    def setAudioOutput(self, audio):
        self.audio = audio

    def setVideoSink(self, sink):
        self.sink = sink

    def setLoops(self, loops):
        self.loops = loops

    def setPlaybackRate(self, rate):
        self.rate = rate

    def setSource(self, source):
        self.source = source

    def play(self):
        self.calls.append('play')

    def pause(self):
        self.calls.append('pause')

    def stop(self):
        self.calls.append('stop')

    def position(self):
        return 2000


class Audio(QObject):
    def setMuted(self, muted):
        self.muted = muted

    def setVolume(self, volume):
        self.volume = volume


def image(color='red', width=20, height=10):
    result = QImage(width, height, QImage.Format.Format_RGBA8888)
    result.fill(QColor(color))
    return result


def media(tmp_path, **changes):
    path = tmp_path / 'silent.fixture'
    path.write_bytes(b'No real decoder or audio device is used')
    return SceneMediaFrame({'type': 'VIDEO', 'file_path': str(path), 'opacity': 100,
                            **changes}, preview=True, providers={'player': Player, 'audio': Audio})


def test_muted_preview_plays_only_when_enabled_and_releases_sink(tmp_path):
    source = media(tmp_path, volume=25, play_rate=150)
    player, audio = source.media_player, source.audio_output
    assert player.calls == [] and audio.muted and audio.volume == .25
    assert player.rate == 1.5
    source.set_active(True)
    source.set_active(True)
    source.set_muted(False)
    source.set_active(False)
    assert player.calls == ['play', 'pause'] and not audio.muted
    source.close()
    source.shutdown()
    assert source.closed and not source.active and source.frame.isNull()
    assert player.calls == ['play', 'pause', 'stop']
    assert player.source == QUrl() and player.sink is None and player.audio is None


def test_sink_retains_latest_frame_without_python_decoder_callbacks(tmp_path):
    source = media(tmp_path)
    delivered = []
    source.frame_changed.connect(lambda: delivered.append(source.frame.pixelColor(1, 1)))

    for color in ['red'] * 100 + ['blue']:
        source.sink.setVideoFrame(QVideoFrame(image(color)))
    assert source.frame.isNull()
    source.set_active(True)
    source.refresh_frame()
    assert delivered == [QColor('blue')]
    source.sink.setVideoFrame(QVideoFrame(image('green')))
    source.shutdown()
    source.refresh_frame()
    QApplication.processEvents()
    assert source.frame.isNull() and delivered == [QColor('blue')]
    source.close()


def test_frame_is_detached_bounded_and_preserves_aspect(tmp_path):
    source = media(tmp_path)
    large = image(width=2560, height=1280)
    source.set_frame(large)
    large.fill(QColor('blue'))
    assert source.frame.size().width() == 1280 and source.frame.height() == 640
    assert source.frame.pixelColor(1, 1) == QColor('red')
    source.resize(40, 20)
    assert source.output_frame().pixelColor(1, 1) == QColor('red')
    source.close()


@pytest.mark.parametrize('changes', [{'volume': True}, {'volume': 101}, {'play_rate': 0},
                                    {'play_rate': float('nan')}, {'play_rate': {}}])
def test_bad_media_options_close_partial_players(tmp_path, changes):
    with pytest.raises(ValueError):
        media(tmp_path, **changes)


class PreviewSource(QWidget):
    frame_changed = Signal()
    failed = Signal(str)

    def __init__(self, entry, *, preview):
        super().__init__()
        assert preview
        self.entry, self.closed, self.active, self.muted = entry, False, False, True
        self.frame = image()
        self.interactions = 0

    def output_frame(self):
        return self.frame

    def set_active(self, active):
        self.active = active

    def set_muted(self, muted):
        self.muted = muted

    def interact(self):
        self.interactions += 1

    def closeEvent(self, event):
        self.closed, self.active = True, False
        self.frame = QImage()
        super().closeEvent(event)


def test_preview_opt_in_geometry_reuse_replace_suspend_and_clear():
    editor = QWidget()
    editor.show()
    preview = SceneMediaPreview(editor, factory=PreviewSource)
    entry = {'type': 'WEB', 'url': 'https://example.invalid'}
    preview.sync({'web': entry})
    assert preview.sources == {}
    preview.set_enabled(True)
    first = preview.sources['web']
    assert first.active and first.muted
    preview.sync({'web': {**entry, 'x': 50, 'width': 1000}})
    assert preview.sources['web'] is first
    preview.interact('web')
    preview.audition('web')
    assert first.interactions == 1 and not first.muted
    preview.suspend()
    assert not first.active
    preview.resume()
    assert first.active
    preview.sync({'web': {**entry, 'url': 'about:blank'}})
    second = preview.sources['web']
    assert second is not first and first.closed
    preview.set_enabled(False)
    assert second.closed and preview.sources == {} and preview.image('web') is None
    preview.shutdown()
    preview.set_enabled(True)
    assert preview.sources == {}
    editor.close()


def test_preview_limit_missing_resource_and_visibility_are_explicit():
    editor = QWidget()
    editor.show()
    preview = SceneMediaPreview(editor, factory=PreviewSource)
    preview.sync({str(i): {'type': 'VIDEO', 'file_path': str(i), 'visible': i != 0}
                  for i in range(10)})
    preview.set_enabled(True)
    assert len(preview.sources) == 8 and set(preview.errors) == {'8', '9'}
    assert not preview.sources['0'].active and preview.sources['1'].active
    removed = preview.sources['1']
    preview.sync({'0': {'type': 'VIDEO', 'file_path': '0'}})
    assert removed.closed and len(preview.sources) == 1 and not preview.errors
    preview.shutdown()
    editor.close()


def test_two_views_keep_source_active_until_last_hidden():
    from frontengine.show.scene.scene import SceneManager
    from frontengine.show.scene.compositor_view import SceneCompositorView
    manager = SceneManager()
    source = PreviewSource({'type': 'WEB'}, preview=True)
    manager.widget_list.append(manager.graphic_scene.addWidget(source))
    first = SceneCompositorView(manager.graphic_scene, 'software')
    second = SceneCompositorView(manager.graphic_scene, 'software')
    first.show()
    second.show()
    assert source.active
    first.hide()
    assert source.active
    second.hide()
    assert not source.active
    first.close()
    second.close()
    manager.clear()
    assert source.closed
