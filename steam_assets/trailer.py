r"""
Record the pet home trailer from the real application.

Run from the repository root::

    .venv\Scripts\python.exe steam_assets/trailer.py [--out FILE] [--stills DIR] [--sound WAV]

Nothing here is a mock-up. A fresh settings folder is made in a temporary directory, the real
Pet home page is opened offscreen at 1920x1080, and a drawn pointer presses its real buttons and
tabs. The only things done behind the interface set the scene: the saved pets, home coins for
the shop, and the clock. The home runs on a film clock instead of the wall clock, so every frame
is exactly 1/30 s of film however long it took to draw, and quiet stretches can run faster.

The film is H.264 at 1920x1080 and 30 fps, written by Qt Multimedia (QVideoFrameInput into a
QMediaRecorder). It has no sound unless --sound names a 16-bit PCM WAV (music, say), which is
looped under the film and faded out with it. --stills writes a JPEG every half second instead,
for checking a cut without encoding.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
import wave
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WIDTH, HEIGHT, FPS = 1920, 1080, 30
VIDEO_BITRATE = 8_000_000        # about 70 s stays well under GitHub's 100 MB
SOUND_VOLUME = 0.55


def _workspace() -> Path:
    """One fixed settings folder per script, emptied at the start of each run.

    A fresh ``mkdtemp`` per run left a folder behind every time: the page's settings lock is still
    held when the script ends, so it cannot clean up after itself. Reusing one name per script
    keeps it to a single folder, and the trailer and the store art can still run side by side."""
    import shutil
    folder = Path(tempfile.gettempdir()) / f"frontengine-{Path(sys.argv[0]).stem or 'steam'}-staging"
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True, exist_ok=True)
    return folder


LAUNCH_DIR = Path.cwd()         # paths on the command line are relative to here, not the workspace
WORKSPACE = _workspace()


def _offscreen_screen() -> None:
    """A 1920x1080 offscreen screen with the system fonts, so the home is as wide as on a real monitor.

    The settings folder is a fresh temporary one, which is also where the screen file goes: the
    platform argument is split at colons, so the file has to be named without a drive letter."""
    os.chdir(WORKSPACE)
    (WORKSPACE / "screen.json").write_text(json.dumps({"screens": [{
        "name": "primary", "x": 0, "y": 0, "width": WIDTH, "height": HEIGHT,
        "logicalDpiX": 96, "logicalDpiY": 96, "dpr": 1}]}), encoding="utf-8")
    os.environ["QT_QPA_PLATFORM"] = "offscreen:configfile=screen.json"
    if sys.platform == "win32":
        os.environ.setdefault("QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"))
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"


_offscreen_screen()
sys.path.insert(0, str(REPO))

from PySide6.QtCore import QPoint, QPointF, QRectF, QSize, Qt, QUrl  # noqa: E402
from PySide6.QtGui import (QColor, QFont, QImage, QLinearGradient, QPainter, QPainterPath,  # noqa: E402
                           QPen, QPolygonF)
from PySide6.QtMultimedia import (QAudioBuffer, QAudioBufferInput, QAudioFormat,  # noqa: E402
                                  QMediaCaptureSession, QMediaFormat, QMediaRecorder, QVideoFrame,
                                  QVideoFrameFormat, QVideoFrameInput)
from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

# ----- film timing ------------------------------------------------------------------------------

FADE_S = 0.6
CAPTION_FADE_S = 0.4
POINTER_SCALE = 1.6
PAGE_SCALE = 1.5
CAPTION_PX = 46
CAPTION_COLOR = QColor("#fff4dc")
ACCENT = QColor("#ff7a3d")


class FilmClock:
    """Film seconds (what the viewer sees) and home seconds (what the pets live through)."""

    def __init__(self) -> None:
        self.film = 0.0
        self.home = 1000.0

    def film_now(self) -> float:
        return self.film

    def home_now(self) -> float:
        return self.home


CLOCK = FilmClock()


def _use_film_clock() -> None:
    """Character animation, weather and badges read ``monotonic``; on film they read the film clock."""
    from frontengine.show.pet_game import home_view, resident_art, strip_weather
    for module in (resident_art, strip_weather):
        module.monotonic = CLOCK.film_now
    home_view.monotonic = CLOCK.film_now


# ----- output -----------------------------------------------------------------------------------

class Recorder:
    """Frames and sound into an MP4 through Qt Multimedia, waiting whenever the encoder is busy."""

    def __init__(self, app: QApplication, out: Path, sound: bytes | None = None, rate: int = 0,
                 channels: int = 0) -> None:
        """``sound`` is 16-bit PCM; without it the film has no sound track at all."""
        self.app = app
        video = QVideoFrameFormat(QSize(WIDTH, HEIGHT), QVideoFrameFormat.PixelFormat.Format_BGRA8888)
        video.setStreamFrameRate(FPS)
        self.video = QVideoFrameInput(video)
        self.session = QMediaCaptureSession()
        self.session.setVideoFrameInput(self.video)
        self.recorder = QMediaRecorder()
        self.session.setRecorder(self.recorder)
        media = QMediaFormat(QMediaFormat.FileFormat.MPEG4)
        media.setVideoCodec(QMediaFormat.VideoCodec.H264)
        self.audio = None
        if sound is not None:
            audio = QAudioFormat()
            audio.setSampleRate(rate)
            audio.setChannelCount(channels)
            audio.setSampleFormat(QAudioFormat.SampleFormat.Int16)
            self.audio_format = audio
            self.audio = QAudioBufferInput(audio)
            self.session.setAudioBufferInput(self.audio)
            media.setAudioCodec(QMediaFormat.AudioCodec.AAC)
            self.recorder.setAudioSampleRate(rate)
            self.recorder.setAudioBitRate(192_000)
        self.recorder.setMediaFormat(media)
        self.recorder.setVideoResolution(QSize(WIDTH, HEIGHT))
        self.recorder.setVideoFrameRate(FPS)
        self.recorder.setVideoBitRate(VIDEO_BITRATE)
        self.recorder.setQuality(QMediaRecorder.Quality.VeryHighQuality)
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.exists():
            out.unlink()
        self.recorder.setOutputLocation(QUrl.fromLocalFile(str(out)))
        self.errors: list[str] = []
        self.recorder.errorOccurred.connect(lambda _code, text: self.errors.append(text))
        self.sound, self.rate, self.channels = sound, rate, channels
        self.frame_bytes = 2 * channels
        self.sent_samples = 0
        self.fade: tuple[int, int] | None = None      # (first sample, length) of the closing fade
        self.frames = 0
        self.recorder.record()

    def fade_sound(self, seconds: float) -> None:
        """Fade the sound out over the next ``seconds``, with the closing fade to black.

        The film's length is only known once it has been shot, so the soundtrack cannot carry its
        own fade-out: a fade baked into a fixed-length track ends up after the film has finished
        and the sound stops dead under the last black frame."""
        if self.audio is not None:
            self.fade = (self.sent_samples, max(1, int(seconds * self.rate)))

    def _gain(self, chunk: bytes, first: int) -> bytes:
        if self.fade is None:
            return chunk
        import numpy as np
        start, length = self.fade
        samples = np.frombuffer(chunk, dtype=np.int16).reshape((-1, self.channels)).astype(np.float32)
        index = np.arange(first, first + len(samples), dtype=np.float32)
        gain = np.clip(1.0 - (index - start) / length, 0.0, 1.0)
        return (samples * gain[:, None]).astype(np.int16).tobytes()

    def _wait(self, send) -> None:
        deadline = time.monotonic() + 30
        while not send():
            if self.errors:
                raise RuntimeError("; ".join(self.errors))
            if time.monotonic() > deadline:
                raise RuntimeError("The encoder stopped taking frames")
            self.app.processEvents()
            time.sleep(0.002)

    def add(self, image: QImage) -> None:
        frame = QVideoFrame(image.convertToFormat(QImage.Format.Format_ARGB32))
        start = int(self.frames * 1_000_000 / FPS)
        frame.setStartTime(start)
        frame.setEndTime(int((self.frames + 1) * 1_000_000 / FPS))
        self._wait(lambda: self.video.sendVideoFrame(frame))
        self.frames += 1
        self._send_sound(self.frames / FPS)

    def _send_sound(self, until_s: float) -> None:
        if self.audio is None:
            return
        target = int(until_s * self.rate)
        while self.sent_samples < target:
            count = min(4096, target - self.sent_samples)
            begin = self.sent_samples * self.frame_bytes
            chunk = self.sound[begin:begin + count * self.frame_bytes]
            chunk += bytes(count * self.frame_bytes - len(chunk))
            chunk = self._gain(chunk, self.sent_samples)
            buffer = QAudioBuffer(chunk, self.audio_format, int(self.sent_samples * 1_000_000 / self.rate))
            self._wait(lambda: self.audio.sendAudioBuffer(buffer))
            self.sent_samples += count

    def close(self) -> None:
        self.recorder.stop()
        deadline = time.monotonic() + 60
        while self.recorder.recorderState() != QMediaRecorder.RecorderState.StoppedState:
            if time.monotonic() > deadline:
                raise RuntimeError("The recording did not finish")
            self.app.processEvents()
            time.sleep(0.01)
        if self.errors:
            raise RuntimeError("; ".join(self.errors))


class Stills:
    """Rehearsal output: a JPEG every half second instead of a film."""

    def __init__(self, folder: Path) -> None:
        self.folder = folder
        folder.mkdir(parents=True, exist_ok=True)
        self.frames = 0

    def add(self, image: QImage) -> None:
        if self.frames % (FPS // 2) == 0:
            image.save(str(self.folder / f"{self.frames // FPS:03d}_{self.frames % FPS:02d}.jpg"), "JPG", 90)
        self.frames += 1

    def fade_sound(self, seconds: float) -> None:
        pass

    def close(self) -> None:
        pass


def soundtrack(path: Path, seconds: float) -> tuple[bytes, int, int]:
    """A 16-bit PCM WAV, looped to ``seconds`` and faded in, as the soundtrack.

    No sound by default: the home's own ambience is birdsong by day and crickets by night, and
    animal calls under a trailer were not wanted. Music can be given with --sound. The track is cut
    longer than the film on purpose; the Recorder fades it out with the closing card."""
    with wave.open(str(path), "rb") as source:
        rate, channels, width = source.getframerate(), source.getnchannels(), source.getsampwidth()
        data = source.readframes(source.getnframes())
    if width != 2:
        raise ValueError("The soundtrack must be a 16-bit PCM WAV")
    import numpy as np
    samples = np.frombuffer(data, dtype=np.int16).reshape((-1, channels)).astype(np.float32)
    total = int(seconds * rate)
    looped = np.resize(samples, (total, channels))
    envelope = np.ones(total, dtype=np.float32)
    fade_in = int(1.0 * rate)
    envelope[:fade_in] = np.linspace(0, 1, fade_in)
    looped *= (envelope * SOUND_VOLUME)[:, None]
    return np.clip(looped, -32768, 32767).astype(np.int16).tobytes(), rate, channels


# ----- the overlay: pointer, click ring, captions, fades ----------------------------------------

def _font(pixels: int, bold: bool = True) -> QFont:
    font = QFont("Segoe UI")
    font.setPixelSize(pixels)
    font.setBold(bold)
    return font


def outlined_text(painter: QPainter, rect: QRectF, text: str, pixels: int, color: QColor, opacity: float,
                  flags=Qt.AlignmentFlag.AlignHCenter) -> None:
    """Text with a dark edge, so it reads over a light home and a dark page alike."""
    if opacity <= 0 or not text:
        return
    font = _font(pixels)
    painter.save()
    painter.setOpacity(opacity)
    painter.setFont(font)
    metrics = painter.fontMetrics()
    lines = text.split("\n")
    y = rect.top() + metrics.ascent()
    for line in lines:
        width = metrics.horizontalAdvance(line)
        x = rect.left() + (rect.width() - width) / 2 if flags & Qt.AlignmentFlag.AlignHCenter else rect.left()
        path = QPainterPath()
        path.addText(QPointF(x, y), font, line)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.strokePath(path, QPen(QColor(20, 14, 10, 230), pixels * 0.16, Qt.PenStyle.SolidLine,
                                      Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.fillPath(path, color)
        y += metrics.height() * 1.08
    painter.restore()


ARROW = [(0, 0), (0, 17), (4.2, 13), (7.2, 20), (10, 18.8), (7.2, 12.2), (12.5, 12.2)]


def draw_pointer(painter: QPainter, point: QPointF, ring: float | None) -> None:
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    if ring is not None:
        radius = 8 + 30 * ring
        painter.setPen(QPen(QColor(255, 122, 61, int(255 * (1 - ring))), 4))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(point, radius, radius)
    polygon = QPolygonF([QPointF(point.x() + x * POINTER_SCALE, point.y() + y * POINTER_SCALE) for x, y in ARROW])
    painter.setPen(QPen(QColor(20, 20, 20), 2))
    painter.setBrush(QColor(255, 255, 255))
    painter.drawPolygon(polygon)
    painter.restore()


def ease(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


# ----- the film ---------------------------------------------------------------------------------

class Film:
    """Owns the page, the clock and the output; each shot calls ``frame`` once per 1/30 s."""

    def __init__(self, app: QApplication, sink, page, logo: QImage) -> None:
        self.app, self.sink, self.page, self.logo = app, sink, page, logo
        self.pointer = QPointF(WIDTH * 0.62, HEIGHT * 0.7)
        self.ring: float | None = None
        self.caption = ""
        self.caption_alpha = 0.0
        self.black = 1.0          # 1 = fully black, faded by shots
        self.speed = 1.0          # home seconds per film second

    # --- one frame
    def frame(self, render) -> None:
        CLOCK.film += 1 / FPS
        service = self.page.service
        # The home drops gaps over five seconds (sleep, a stalled loop), so a time-lapse frame is
        # fed to it as several one-second steps.
        remaining = self.speed / FPS
        while remaining > 0:
            step = min(1.0, remaining)
            CLOCK.home += step
            remaining -= step
            if service.world is not None:
                service._tick()
        self.app.processEvents()
        image = render()
        painter = QPainter(image)
        if render == self.page_shot:         # the pointer belongs to the interface, not to the views
            draw_pointer(painter, self.pointer, self.ring)
        top = HEIGHT * (0.12 if render == self.desktop else 0.83)
        outlined_text(painter, QRectF(0, top, WIDTH, 140), self.caption, CAPTION_PX,
                      CAPTION_COLOR, self.caption_alpha)
        if self.black > 0:
            painter.fillRect(0, 0, WIDTH, HEIGHT, QColor(0, 0, 0, int(255 * min(1.0, self.black))))
        painter.end()
        self.sink.add(image)

    def hold(self, seconds: float, render, *, fade_in: bool = False, fade_out: bool = False) -> None:
        count = max(1, round(seconds * FPS))
        for index in range(count):
            t = index / FPS
            if fade_in:
                self.black = max(0.0, 1 - t / FADE_S)
            if fade_out:
                self.black = max(0.0, 1 - (seconds - t) / FADE_S)
            if self.caption:
                self.caption_alpha = min(1.0, self.caption_alpha + 1 / (CAPTION_FADE_S * FPS))
            else:
                self.caption_alpha = 0.0
            if self.ring is not None:
                self.ring = self.ring + 1 / (0.45 * FPS)
                if self.ring >= 1:
                    self.ring = None
            self.frame(render)

    def say(self, text: str) -> None:
        self.caption = text
        self.caption_alpha = 0.0

    # --- the hand: move to a widget and press it, as a viewer would
    def point_at(self, widget: QWidget, local: QPoint | None = None) -> QPointF:
        local = local or widget.rect().center()
        point = widget.mapTo(self.page, local)
        return QPointF(point.x() * PAGE_SCALE, point.y() * PAGE_SCALE)

    def move(self, target: QPointF, seconds: float, render) -> None:
        start = QPointF(self.pointer)
        count = max(1, round(seconds * FPS))
        for index in range(1, count + 1):
            k = ease(index / count)
            self.pointer = QPointF(start.x() + (target.x() - start.x()) * k,
                                   start.y() + (target.y() - start.y()) * k)
            self.hold(1 / FPS, render)

    def click(self, widget: QWidget, render, local: QPoint | None = None, action=None) -> None:
        self.move(self.point_at(widget, local), 0.8, render)
        self.hold(0.15, render)
        self.ring = 0.0
        if action is not None:
            action()
        elif hasattr(widget, "click"):
            widget.click()
        self.hold(0.5, render)

    def scroll_to(self, scroll, target: int, seconds: float, render) -> None:
        bar = scroll.verticalScrollBar()
        start, target = bar.value(), max(bar.minimum(), min(bar.maximum(), int(target)))
        if start == target:
            return
        count = max(1, round(seconds * FPS))
        for index in range(1, count + 1):
            bar.setValue(int(start + (target - start) * ease(index / count)))
            self.hold(1 / FPS, render)

    def top(self, render, seconds: float = 0.8) -> None:
        scroll = getattr(self.page, "_scroll", None)
        if scroll is not None:
            self.scroll_to(scroll, 0, seconds, render)

    def tab(self, label: str, render) -> None:
        tabs = self.page.tabs
        index = next(i for i in range(tabs.count()) if tabs.tabText(i).replace("&", "") == label)
        bar = tabs.tabBar()
        scroll = getattr(self.page, "_scroll", None)
        if scroll is not None:      # bring the tabs up as a viewer would scroll down to them
            target = bar.mapTo(scroll.widget(), QPoint(0, 0)).y() - 40
            self.scroll_to(scroll, target, 0.8, render)
        self.click(bar, render, bar.tabRect(index).center(), action=lambda: tabs.setCurrentIndex(index))

    # --- what a frame shows
    def page_shot(self) -> QImage:
        """The page drawn at 1.5x, as on a 150 % display, so its text can be read in a film."""
        image = QImage(WIDTH, HEIGHT, QImage.Format.Format_ARGB32)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        painter.scale(PAGE_SCALE, PAGE_SCALE)
        self.page.render(painter, QPoint(0, 0))
        painter.end()
        return image

    def pan(self, scale: float, start: float, end: float, seconds: float):
        """A close-up whose camera glides from ``start`` to ``end`` (view pixels) over ``seconds``."""
        view, count, state = self.page.view, max(1, round(seconds * FPS)), {"frame": 0}

        def render() -> QImage:
            k = ease(min(1.0, state["frame"] / count))
            state["frame"] += 1
            return close_up_image(view, scale, start + (end - start) * k)
        return render

    def close_up(self, scale: float, center: float | None = None):
        """The home drawing redrawn larger (not an enlarged screenshot), centred on what is in it."""
        view = self.page.view
        camera = {"x": center if center is not None else pets_center(self.page)}
        follow = center is None

        def render() -> QImage:
            if follow:      # drift after the pets instead of letting them walk out of the picture
                camera["x"] += (pets_center(self.page) - camera["x"]) * 0.03
            return close_up_image(view, scale, camera["x"])
        return render

    def desktop(self) -> QImage:
        return desktop_image(self.page)

    def card(self) -> QImage:
        return card_image(self.logo)


def close_up_image(view, scale: float, center_x: float, width: int = WIDTH, height: int = HEIGHT,
                   floor_at: float = 0.74) -> QImage:
    """The home drawing redrawn larger (not an enlarged screenshot), centred on ``center_x``."""
    image = QImage(width, height, QImage.Format.Format_ARGB32)
    drawn = QImage(int(view.width() * scale), int(view.height() * scale), QImage.Format.Format_ARGB32)
    drawn.fill(Qt.GlobalColor.transparent)
    painter = QPainter(drawn)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.scale(scale, scale)
    view.render(painter, QPoint(0, 0))
    painter.end()

    def common(y: int) -> QColor:
        # Several columns: a single pixel can land on a falling petal.
        samples = [drawn.pixel(int(drawn.width() * k / 10), y) for k in range(1, 10)]
        return QColor(max(set(samples), key=samples.count))
    top, bottom = common(4), common(drawn.height() - 3)
    painter = QPainter(image)
    painter.fillRect(0, 0, width, height, top)      # the home's own sky, carried up seamlessly
    x = width / 2 - center_x * scale
    x = min(0.0, max(width - drawn.width(), x)) if drawn.width() > width else (width - drawn.width()) / 2
    y = height * floor_at - drawn.height()
    painter.drawImage(QPointF(x, y), drawn)
    painter.fillRect(QRectF(0, y + drawn.height() - 2, width, height), bottom)
    painter.end()
    return image


def desktop_image(page) -> QImage:
    """The desktop strip as the desktop shows it: transparent, standing on the taskbar."""
    image = QImage(WIDTH, HEIGHT, QImage.Format.Format_ARGB32)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    wall = QLinearGradient(0, 0, WIDTH, HEIGHT)
    wall.setColorAt(0, QColor("#2b4a6f"))
    wall.setColorAt(0.6, QColor("#3f6f8f"))
    wall.setColorAt(1, QColor("#e3a96b"))
    painter.fillRect(0, 0, WIDTH, HEIGHT, wall)
    taskbar = 48
    painter.fillRect(0, HEIGHT - taskbar, WIDTH, taskbar, QColor(24, 26, 30, 235))
    shot = page.window().grab().toImage().scaled(1000, 560, Qt.AspectRatioMode.KeepAspectRatio,
                                                 Qt.TransformationMode.SmoothTransformation)
    left, top = (WIDTH - shot.width()) // 2, 300
    painter.fillRect(QRectF(left - 2, top - 2, shot.width() + 4, shot.height() + 4), QColor(0, 0, 0, 90))
    painter.drawImage(left, top, shot)
    for strip in page.strip_list:
        strip_image = strip.grab().toImage()
        painter.drawImage(QPoint(strip.x(), HEIGHT - taskbar - strip_image.height()), strip_image)
    painter.end()
    return image


def card_image(logo: QImage) -> QImage:
    image = QImage(WIDTH, HEIGHT, QImage.Format.Format_ARGB32)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
    gradient = QLinearGradient(0, 0, WIDTH, HEIGHT)
    gradient.setColorAt(0, QColor("#1d1a17"))
    gradient.setColorAt(1, QColor("#0f0d0c"))
    painter.fillRect(0, 0, WIDTH, HEIGHT, gradient)
    logo = logo.scaledToWidth(int(WIDTH * 0.42), Qt.TransformationMode.SmoothTransformation)
    painter.drawImage(QPointF((WIDTH - logo.width()) / 2, HEIGHT * 0.36 - logo.height() / 2), logo)
    painter.end()
    return image


# ----- staging ----------------------------------------------------------------------------------

PET_NAMES = ("Mochi", "Pip", "Moss", "Bolt", "Ink", "Gill")


def stage_pets(profiles, count: int = 4) -> set[str]:
    """Saved pets who will move in, each drawn as a different built-in character.

    Profiles cannot be deleted, so a pet that would look like one already chosen is simply left
    unticked in the page's own "moving in" list (see ``tick_movers``)."""
    from frontengine.show.pet_game.resident_art import fallback_character
    chosen: dict[str, str] = {}
    for attempt in range(60):
        if len(chosen) >= count:
            break
        name = PET_NAMES[len(chosen)] if len(chosen) < len(PET_NAMES) else f"Pet {attempt}"
        record = profiles.create(name)
        character = fallback_character(record["id"])
        if character not in chosen:
            chosen[character] = record["id"]
        else:
            profiles.update(record["id"], {"name": "Spare"})
    return set(chosen.values())


def tick_movers(page, movers: set[str]) -> None:
    for row in range(page.newcomers.count()):
        item = page.newcomers.item(row)
        wanted = item.data(Qt.ItemDataRole.UserRole) in movers
        item.setCheckState(Qt.CheckState.Checked if wanted else Qt.CheckState.Unchecked)
        item.setHidden(not wanted)


def wait_for_art(app: QApplication, page, seconds: float = 90) -> None:
    """Characters load in the background; the film goes on once every resident is drawn as itself."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        app.processEvents()
        world = page.service.world
        if world is not None and world.residents and all(
                page.art.renderer(identifier) is not None for identifier in world.residents):
            return
        time.sleep(0.05)
    print("warning: some characters were still loading")


def settle(app: QApplication, seconds: float) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)


def pets_center(page) -> float:
    """The median pet, in view pixels: a close-up follows where most of them are."""
    world, view = page.service.world, page.view
    xs = sorted(view.resident_center(r).x() for r in world.residents.values()) if world else []
    return xs[len(xs) // 2] if xs else view.width() / 2


def home_center(page) -> float:
    """The middle, in view pixels, of everything standing in the home: furniture and pets."""
    world, view = page.service.world, page.view
    if world is None:
        return view.width() / 2
    xs = [view.resident_center(r).x() for r in world.residents.values()]
    zone = page.zone
    for piece, definition in (world.in_zone(zone) if zone else ()):
        xs.append(view.piece_rect(piece, definition).center().x())
    return (min(xs) + max(xs)) / 2 if xs else view.width() / 2


# ----- the script -------------------------------------------------------------------------------

# Pieces the built-in characters have a pose of their own for, set out with a gap between each so
# every use can be seen. Free arranging has every piece, including those a new home has not
# unlocked yet (piano, aquarium, fireplace...).
SHOWROOM = ("bed_cozy", "bookshelf", "armchair", "tv_set", "fireplace", "piano", "easel", "aquarium",
            "toy_box", "telescope", "wardrobe_closet", "kotatsu", "floor_lamp", "plant_pot")


def furnish_showroom(page) -> None:
    """Set the free-arranging home out like a showroom (setting the scene, as with the saved pets)."""
    world, zone = page.service.world, page.zone
    cell = 2                                  # cell 0 is the entrance
    for name in SHOWROOM:
        result, _piece = world.place(name, zone, cell)
        if result != "accepted":
            print(f"warning: {name} not placed ({result})")
        cell += world.catalog.furniture[name].width + 1
    page.refresh()


def furniture_span(page) -> tuple[float, float]:
    world, view = page.service.world, page.view
    xs = [view.piece_rect(piece, definition).center().x() for piece, definition in world.in_zone(page.zone)]
    return (min(xs), max(xs)) if xs else (0.0, float(view.width()))


def ask_everyone(page, command: str) -> None:
    """What the pet menu's *Ask to* does, for every resident."""
    service = page.service
    for identifier in list(service.world.residents):
        service.run(lambda world, i=identifier: world.command(i, command))


def furniture_interactions(film: Film, app: QApplication) -> None:
    """Free arranging, then the pets using the pieces made for what they were asked to do."""
    page, shot = film.page, film.page_shot
    film.say("Free arranging: every piece of furniture, no costs")
    film.top(shot, 0.0)
    film.hold(0.6, shot, fade_in=True)
    film.click(page.sandbox_button, shot)
    # The free-arranging home starts empty; the same four pets move in.
    movers = {page.newcomers.item(i).data(Qt.ItemDataRole.UserRole) for i in range(page.newcomers.count())
              if page.newcomers.item(i).text() != "Spare"}
    tick_movers(page, movers)
    film.hold(0.6, shot)
    film.click(page.create_button, shot)
    furnish_showroom(page)
    wait_for_art(app, page)
    film.hold(1.6, shot)
    film.say("")
    film.hold(0.5, shot, fade_out=True)

    # Off camera, the pets are asked to relax and given a moment to walk over.
    ask_everyone(page, "relax")
    run_home(app, page, 45)
    left, right = furniture_span(page)
    margin = WIDTH / 2 / 2.6
    start, end = left + margin * 0.8, right - margin * 0.8
    film.speed = 1.5
    # Captions stay general: the pets' identities are new every run, so who picks which piece varies.
    film.say("Ask them to relax or play, and each one picks a piece to use")
    film.hold(6.0, film.pan(2.6, start, (start + end) / 2, 6.0), fade_in=True)
    film.say("")
    film.hold(0.5, film.pan(2.6, (start + end) / 2, (start + end) / 2, 0.5), fade_out=True)

    ask_everyone(page, "play")
    run_home(app, page, 45)
    film.say("Every built-in character has a pose of its own for each piece")
    film.hold(6.0, film.pan(2.6, (start + end) / 2, end, 6.0), fade_in=True)
    film.say("")
    film.hold(0.5, film.pan(2.6, end, end, 0.5), fade_out=True)
    film.speed = 3.0


def shoot(film: Film, app: QApplication) -> None:
    page = film.page
    shot = film.page_shot

    film.say("")
    film.hold(2.6, film.card, fade_in=True)
    film.say("Your desktop pets get a home of their own")
    film.hold(2.4, film.card, fade_out=True)

    film.say("Your saved pets move in as themselves")
    film.hold(1.2, shot, fade_in=True)
    film.click(page.create_button, shot)
    settle(app, 1.5)
    wait_for_art(app, page)
    film.hold(1.6, shot)
    film.say("")
    film.hold(0.5, shot, fade_out=True)

    film.say("They live, work and rest on their own")
    film.speed = 3.0
    life = film.close_up(2.6)
    film.hold(5.0, life, fade_in=True)
    film.say("Every pose drawn from the character's own layers, dressed or not")
    film.hold(4.0, life)
    film.say("")
    film.hold(0.5, life, fade_out=True)

    film.speed = 40.0           # off the home view: let the morning reach working hours
    film.say("45 pieces of furniture to buy and arrange")
    film.hold(0.8, shot, fade_in=True)
    film.tab(_tr("pet_home_furniture_section", "Furniture"), shot)
    presets = page.layout_panel.presets
    scroll = page._scroll
    film.scroll_to(scroll, presets.mapTo(scroll.widget(), QPoint(0, 0)).y() - 300, 0.9, shot)
    index = presets.findData("cozy")
    film.click(presets, shot, action=lambda: presets.setCurrentIndex(index))
    film.hold(0.8, shot)
    film.click(page.layout_panel.apply_layout_button, shot)
    film.hold(1.2, shot)
    film.tab(_tr("pet_home_shop_section", "Shop"), shot)
    film.hold(1.2, shot)
    film.say("")
    film.hold(0.5, shot, fade_out=True)

    film.say("Every finished job pays home coins")
    film.hold(0.6, shot, fade_in=True)
    film.tab(_tr("pet_home_work_section", "Work"), shot)
    film.hold(2.4, shot)
    film.say("")
    film.hold(0.5, shot, fade_out=True)

    furniture_interactions(film, app)

    film.say("Days, nights and weather")
    film.speed = 300.0          # a game day is one real hour: a whole day and night in twelve seconds
    lapse = film.close_up(2.4, home_center(page))
    film.hold(12.0, lapse, fade_in=True)
    film.speed = 3.0
    film.say("")
    film.hold(0.5, lapse, fade_out=True)

    page._scroll.verticalScrollBar().setValue(0)      # the window in the next shot shows the home
    film.say("The home also lives on your desktop, along the taskbar.\nClicks pass through everything but the pets.")
    film.hold(6.0, film.desktop, fade_in=True)
    film.say("")
    film.hold(0.5, film.desktop, fade_out=True)

    film.say("Pet home. In FrontEngine now.")
    film.hold(3.5, film.card, fade_in=True)
    film.say("")
    film.sink.fade_sound(1.5)       # the sound goes with the picture
    film.hold(1.5, film.card, fade_out=True)


def _tr(key: str, fallback: str) -> str:
    from frontengine.utils.multi_language.language_wrapper import language_wrapper
    return language_wrapper.language_word_dict.get(key, fallback)


PLANNED_SECONDS = 90          # the soundtrack is cut longer than the film and faded with it


def stage_page(app: QApplication, page) -> None:
    """Set the scene on a Pet home page: saved pets ready to move in, on the film clock, with coins.

    Shared with ``generate.py``, which photographs the same home for the store page."""
    page.service._clock = CLOCK.home_now
    movers = stage_pets(page.profiles)
    page.refresh()
    tick_movers(page, movers)
    # Build the built-in stand-ins now, so the pets appear as themselves the moment they move in.
    from frontengine.show.pet_game import resident_art
    for identifier in movers:
        resident_art._stand_in(resident_art.fallback_character(identifier))
    page.dismiss_intro()
    page.set_strip_scale(150)
    original_create = page.service.create_home

    def create_home(*args, **kwargs):
        # Coins for the shop and the layout: setting the scene, like the saved pets.
        result = original_create(*args, **kwargs)
        page.service.world.ledger.apply("trailer-savings", "trailer", 600)
        return result
    page.service.create_home = create_home
    settle(app, 1.0)


def run_home(app: QApplication, page, home_seconds: float) -> None:
    """Let the home live ``home_seconds`` on the film clock without filming it."""
    for _ in range(int(home_seconds)):
        CLOCK.home += 1.0
        CLOCK.film += 1.0 / 8
        page.service._tick()
    app.processEvents()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--out", default=str(REPO / "steam_assets" / "trailer_pet_home.mp4"))
    parser.add_argument("--stills", default=None, help="write JPEG stills to this folder instead of a film")
    parser.add_argument("--sound", default=None,
                        help="a 16-bit PCM WAV to loop under the film; without it the film is silent")
    args = parser.parse_args()

    (WORKSPACE / "user_setting.json").write_text(json.dumps({"language": "English"}), encoding="utf-8")

    app = QApplication([])
    app.setApplicationName("FrontEngine")
    _use_film_clock()

    from frontengine.ui.runtime_lifetime import DefaultSettingsLifetime
    lifetime = DefaultSettingsLifetime.open()
    from frontengine.user_setting.user_setting_file import read_user_setting
    read_user_setting()
    from frontengine.utils.multi_language.language_wrapper import language_wrapper
    language_wrapper.reset_language("English")
    from frontengine.ui.style.app_style import apply_app_style
    from frontengine.ui.page.pet_game.home_page import PetHomePage

    page = PetHomePage(lifetime=lifetime)
    apply_app_style(page, "dark", application=True)
    page.resize(int(WIDTH / PAGE_SCALE), int(HEIGHT / PAGE_SCALE))
    page.show()
    stage_page(app, page)

    logo = QImage(str(REPO / "steam_assets" / "library_logo_1280x720.png"))
    out = LAUNCH_DIR / args.out
    if args.stills:
        sink = Stills(LAUNCH_DIR / args.stills)
    elif args.sound:
        sink = Recorder(app, out, *soundtrack(LAUNCH_DIR / args.sound, PLANNED_SECONDS + 5))
    else:
        sink = Recorder(app, out)
    film = Film(app, sink, page, logo)
    shoot(film, app)
    sink.close()
    seconds = sink.frames / FPS
    print(f"{sink.frames} frames, {seconds:.1f} s" + ("" if args.stills else f" -> {out}"))
    os._exit(0)      # the page's lifetime and save thread are not ours to wind down cleanly here


if __name__ == "__main__":
    main()
