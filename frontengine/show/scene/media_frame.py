"""Bounded raster frames from Qt video/web and native Imervue rendering."""
from __future__ import annotations

from pathlib import Path
import math

from PySide6.QtCore import Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QImage, QColor
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer, QVideoSink
from PySide6.QtWebEngineCore import QWebEnginePage
from shiboken6 import isValid

from frontengine.show.base_widget import BaseWidget
from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.power_mode.power_mode import tier_interval
from frontengine.utils.multi_language.retranslate import translate


class SceneMediaFrame(BaseWidget):
    """One media owner with retained frames, explicit activity and idempotent close."""

    frame_changed = Signal()
    failed = Signal(str)

    def __init__(self, entry: dict, *, preview: bool = False, providers: dict | None = None) -> None:
        super().__init__()
        self.entry, self.preview = dict(entry), preview
        self.providers = providers or {}
        self.frame = QImage()
        self.error = ''
        self.active = False
        self.closed = False
        self.host = None
        self.media_player = None
        self.audio_output = None
        self.profile_pet = None
        self.overlay_remembers_geometry = False
        size = entry.get('size', (320, 480)) if entry.get('type') == 'PUPPET' else (320, 180)
        self.resize(int(entry.get('width', size[0])), int(entry.get('height', size[1])))
        default_opacity = 100 if entry.get('type') == 'PUPPET' else 20
        self.opacity = 1.0 if preview else entry.get('opacity', default_opacity) / 100
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_frame)
        self.apply_quality_tier()
        try:
            self._build_source()
        except (OSError, ValueError, RuntimeError):
            self.shutdown()
            self.close()
            raise

    def _build_source(self) -> None:
        kind = self.entry.get('type')
        if kind in ('VIDEO', 'SOUND'):
            self._build_player()
        elif kind == 'WEB':
            self._build_web()
        elif kind == 'PUPPET':
            self._build_puppet()
        else:
            raise ValueError(f'Unsupported frame source: {kind}')

    def _build_player(self) -> None:
        path = Path(self.entry.get('file_path', ''))
        if not path.is_file():
            raise ValueError('Media source must be an existing file')
        self.media_player = self.providers.get('player', QMediaPlayer)(self)
        self.audio_output = self.providers.get('audio', QAudioOutput)(self)
        self.audio_output.setVolume(self._fraction('volume', 100))
        self.audio_output.setMuted(self.preview)
        self.media_player.setAudioOutput(self.audio_output)
        self.sink = QVideoSink(self)
        # Poll Qt's single retained frame. A Python direct decoder callback can
        # deadlock native stop() waiting for the producer thread to acquire GIL.
        self.media_player.setVideoSink(self.sink)
        self.media_player.setLoops(QMediaPlayer.Loops.Infinite)
        self.media_player.setPlaybackRate(self._fraction('play_rate', 1000))
        self.media_player.positionChanged.connect(self._position_changed, Qt.ConnectionType.QueuedConnection)
        self.media_player.errorOccurred.connect(self._player_failed, Qt.ConnectionType.QueuedConnection)
        self.media_player.setSource(QUrl.fromLocalFile(str(path.resolve())))

    def _position_changed(self, _position: int) -> None:
        if not self.closed:
            self.update()

    def _player_failed(self, _code, message: str) -> None:
        self._fail(message)

    def _fraction(self, field: str, maximum: int) -> float:
        value = self.entry.get(field, 100)
        if isinstance(value, bool):
            raise ValueError(f'Media {field} must be a finite percentage')
        try:
            value = float(value)
        except (TypeError, ValueError, OverflowError) as error:
            raise ValueError(f'Media {field} must be a finite percentage') from error
        if not math.isfinite(value) or not 0 <= value <= maximum or (field == 'play_rate' and value == 0):
            raise ValueError(f'Media {field} must be within its supported range')
        return value / 100

    def _build_web(self) -> None:
        from PySide6.QtWebEngineWidgets import QWebEngineView
        url = self.entry.get('url')
        if not isinstance(url, str) or not url.strip():
            raise ValueError('Web frame requires a URL')
        self.host = self.providers.get('web', QWebEngineView)()
        self.host.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
        self.host.resize(min(self.width(), 1280), min(self.height(), 1280))
        self.host.page().setBackgroundColor(QColor(Qt.GlobalColor.transparent))
        self.host.loadFinished.connect(lambda success: None if success else self._fail('Web preview failed to load'))
        self.host.renderProcessTerminated.connect(lambda _status, _code: self._fail('Web renderer stopped'))
        self.host.load(QUrl(url))

    def _build_puppet(self) -> None:
        from frontengine.show.pet.puppet_pet import PuppetPetWidget
        from frontengine.user_setting.pet_profiles import PetProfiles
        self.host = self.providers.get('puppet', PuppetPetWidget)(
            self.entry.get('file_path', ''), size=(min(self.width(), 1280), min(self.height(), 1280)),
            parameters=self.entry.get('parameters'), motion=self.entry.get('motion'),
            expression=self.entry.get('expression'),
            script_path=None if self.preview else self.entry.get('script_path'),
            profiles=PetProfiles({}, lambda: None))
        self.host.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)
        self.host.overlay_remembers_geometry = False
        self.profile_pet = self.host

    def set_frame(self, image: QImage) -> None:
        """Retain one bounded detached image; replacement invalidates the raster cache."""
        if self.closed or image.isNull():
            return
        self.frame = (image.scaled(1280, 1280, Qt.AspectRatioMode.KeepAspectRatio,
                                  Qt.TransformationMode.SmoothTransformation)
                      if max(image.width(), image.height()) > 1280 else image.copy())
        self.error = ''
        self.update()
        self.frame_changed.emit()

    def _fail(self, message: str) -> None:
        if self.closed or message == self.error:
            return
        self.error = message[:500]
        front_engine_logger.warning(f'[SceneMediaFrame] {self.error}')
        self.failed.emit(self.error)
        self.update()
        self.frame_changed.emit()

    def refresh_frame(self) -> None:
        """Read the renderer's own surface, independent of desktop occlusion."""
        if not self.active or self.closed:
            return
        if self.media_player is not None:
            frame = self.sink.videoFrame()
            if frame.isValid():
                self.set_frame(frame.toImage())
            return
        if self.host is None:
            return
        if not isValid(self.host):
            self._fail('The media interaction window was closed')
            self.timer.stop()
            return
        if self.profile_pet is not None:
            if not self.host.canvas.isValid():
                self._fail('Puppet preview requires a native OpenGL context')
                return
            image = self.host.canvas.render_offscreen_puppet(min(self.width(), 1280), min(self.height(), 1280))
        else:
            image = self.host.grab().toImage()
        if image is not None:
            self.set_frame(image)

    def set_active(self, active: bool) -> None:
        """Suspend hidden previews; resume media and renderer timers explicitly."""
        if self.closed or active == self.active:
            return
        self.active = active
        if self.media_player is not None:
            self.media_player.play() if active else self.media_player.pause()
        if self.host is not None and isValid(self.host):
            if not active:
                self.host.hide()
            if self.profile_pet is None:
                state = QWebEnginePage.LifecycleState.Active if active else QWebEnginePage.LifecycleState.Frozen
                self.host.page().setLifecycleState(state)
            if active:
                self.host.show()
        self.timer.start() if active else self.timer.stop()

    def interact(self) -> None:
        """Expose the same live native renderer for web forms or puppet hit areas."""
        self.set_active(True)
        if self.host is not None and isValid(self.host):
            self.host.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, False)
            self.host.show()
            self.host.raise_()
            self.host.activateWindow()

    def set_muted(self, muted: bool) -> None:
        """Only explicit audition may unmute an editor preview."""
        if self.audio_output is not None:
            self.audio_output.setMuted(bool(muted))

    def apply_quality_tier(self) -> None:
        if hasattr(self, 'timer'):
            self.timer.setInterval(tier_interval(100 if self.preview else 33, self.quality_tier))

    def draw_content(self, painter) -> None:
        if not self.frame.isNull():
            painter.drawImage(self.rect(), self.frame)
        elif self.preview and self.entry.get('type') == 'SOUND' and self.media_player is not None:
            painter.setPen(QColor('white'))
            label = translate('scene_media_audio').format(
                name=Path(self.entry.get('file_path', '')).name,
                seconds=self.media_player.position() // 1000)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, label)

    def shutdown(self) -> None:
        """Stop native/media work before releasing handles and retained frames."""
        if self.closed:
            return
        self.closed, self.active = True, False
        self.timer.stop()
        if self.media_player is not None:
            self.media_player.stop()
            self.media_player.setSource(QUrl())
            self.media_player.setVideoSink(None)
            self.media_player.setAudioOutput(None)
        if self.host is not None and isValid(self.host):
            if self.profile_pet is not None:
                self.host.shutdown()
            else:
                self.host.stop()
                self.host.page().setLifecycleState(QWebEnginePage.LifecycleState.Discarded)
            self.host.close()
            self.host.deleteLater()
        self.frame = QImage()

    def closeEvent(self, event) -> None:
        self.shutdown()
        super().closeEvent(event)
