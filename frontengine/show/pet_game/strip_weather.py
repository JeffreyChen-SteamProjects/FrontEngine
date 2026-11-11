"""Rain and snow over the desktop home strip, in a window of its own that never takes input.

The strip limits itself to its pieces, pets and ⌂ button with a window mask so the rest
of the desktop stays clickable, and on Windows that mask clips drawing too: weather
painted on the strip itself could never be seen. This layer sits exactly over the strip,
is transparent for input (every click falls through to the strip or the windows behind)
and never takes focus. It shows only while the strip shows and it rains or snows, and not
in focus or meeting mode; under *Reduce motion* the drops stand still.
"""
from __future__ import annotations

from time import monotonic

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from frontengine.utils.pet_game.environment import weather

RAIN_COLOR = QColor(105, 145, 210, 170)
SNOW_COLOR = QColor(250, 250, 255, 220)
SNOW_EDGE = QColor(120, 130, 150, 140)        # keeps flakes visible over a white window
DROPS_PER_100_PX = 6
FLAKES_PER_100_PX = 2
# R2 low-discrepancy sequence: drops spread evenly without lining up into stripes.
_PLASTIC = 1.32471795724474602596
_STEP_X, _STEP_Y = 1 / _PLASTIC, 1 / _PLASTIC ** 2


def _spot(index: int, width: int, height: int, fall: int) -> tuple[float, float]:
    x = ((0.5 + _STEP_X * index) % 1.0) * width
    y = (((0.5 + _STEP_Y * index) % 1.0) * height + fall) % height
    return x, y


def precipitation(home: str, time_ms: int) -> str | None:
    """'rain' or 'snow' while it falls, else None."""
    current = weather(home, time_ms)
    return current if current in ("rain", "snow") else None


def paint_precipitation(painter: QPainter, rect: QRectF, kind: str, elapsed_ms: int, moving: bool) -> None:
    """Slanted rain streaks or round flakes spread evenly over the rectangle."""
    width, height = max(1, int(rect.width())), max(1, int(rect.height()))
    painter.save()
    if kind == "rain":
        painter.setPen(QPen(RAIN_COLOR, 1.4))
        fall = (elapsed_ms // 16) * 6 if moving else 0
        for index in range(max(8, width * DROPS_PER_100_PX // 100)):
            x, y = _spot(index, width, height, fall)
            x = (x - (y // 11)) % width                    # the slant of the fall
            painter.drawLine(QPointF(rect.left() + x, rect.top() + y),
                             QPointF(rect.left() + x - 4, rect.top() + y + 11))
    else:
        painter.setPen(QPen(SNOW_EDGE, 0.8))
        painter.setBrush(SNOW_COLOR)
        fall = (elapsed_ms // 33) if moving else 0
        for index in range(max(6, width * FLAKES_PER_100_PX // 100)):
            sway = (index * 7 + fall // 5) % 9 - 4
            x, y = _spot(index, width, height, fall)
            x = (x + sway) % width
            size = 2.6 if index % 3 else 3.6
            painter.drawEllipse(QPointF(rect.left() + x, rect.top() + y), size, size)
    painter.restore()


class StripWeather(QWidget):
    """Follows one strip's geometry, layer and visibility; owns no timer of its own."""

    def __init__(self, strip) -> None:
        super().__init__(None)
        self.strip = strip
        self.kind: str | None = None
        self._started = monotonic()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.apply_layer()

    def apply_layer(self) -> None:
        from frontengine.show.pet_game.home_strip import strip_flags
        visible = self.isVisible()
        self.setWindowFlags(strip_flags(self.strip.layer) | Qt.WindowType.WindowTransparentForInput)
        if visible:
            self.show()

    def sync(self) -> None:
        """Match the strip and show only while it rains or snows on a shown, non-quiet strip."""
        world = self.strip.service.world
        self.kind = precipitation(world.home, world.time_ms) if world is not None else None
        wanted = self.kind is not None and self.strip.isVisible() and not self.strip.quiet
        if self.geometry() != self.strip.geometry():
            self.setGeometry(self.strip.geometry())
        if wanted and not self.isVisible():
            self.show()
            self.raise_()
        elif not wanted and self.isVisible():
            self.hide()

    def paintEvent(self, _event) -> None:
        if self.kind is None:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        elapsed = int((monotonic() - self._started) * 1000)
        paint_precipitation(painter, QRectF(self.rect()), self.kind, elapsed, not self.strip.reduced_motion)
        painter.end()
