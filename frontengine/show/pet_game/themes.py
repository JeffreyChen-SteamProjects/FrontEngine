"""Theme colours and the sky. Themes change looks only; layout, paths and items never change."""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen

from frontengine.utils.pet_game.environment import daylight, sky, weather

PALETTES = {
    "warm_home": {"floor": (150, 120, 90), "day": (250, 232, 205), "night": (42, 38, 70)},
    "green_studio": {"floor": (104, 136, 88), "day": (222, 240, 214), "night": (28, 50, 44)},
    "night_studio": {"floor": (92, 92, 132), "day": (216, 216, 240), "night": (18, 18, 44)},
}
WEATHER_GLYPHS = {"clear": "☀", "cloudy": "☁", "rain": "☂"}
NIGHT_GLYPH = "☾"
RAIN_DROPS = 60


def palette(theme: str) -> dict:
    return PALETTES.get(theme, PALETTES["warm_home"])


def floor_color(theme: str) -> QColor:
    return QColor(*palette(theme)["floor"], 170)


def sky_color(theme: str, time_ms: int, cloudy: bool) -> QColor:
    """Blend night into day by daylight; clouds grey it a little."""
    colors = palette(theme)
    light = daylight(time_ms)
    mixed = [round(n + (d - n) * light) for d, n in zip(colors["day"], colors["night"])]
    if cloudy:
        mixed = [round(value * 0.85 + 128 * 0.15) for value in mixed]
    return QColor(*mixed)


def glyph(home: str, time_ms: int) -> str:
    """A tiny weather / night sign for the desktop button."""
    if sky(time_ms) == "night" and weather(home, time_ms) == "clear":
        return NIGHT_GLYPH
    return WEATHER_GLYPHS[weather(home, time_ms)]


def paint_sky(painter: QPainter, rect: QRectF, theme: str, home: str, time_ms: int, moving: bool) -> None:
    """The overview's background: time-of-day colour and, when it rains, slanted drops."""
    current = weather(home, time_ms)
    top = sky_color(theme, time_ms, current != "clear")
    gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    gradient.setColorAt(0, top)
    gradient.setColorAt(1, top.lighter(115))
    painter.fillRect(rect, gradient)
    if current != "rain":
        return
    painter.setPen(QPen(QColor(120, 150, 200, 150), 1))
    shift = (time_ms // 50) % 40 if moving else 0          # reduced motion keeps the drops still
    for index in range(RAIN_DROPS):
        x = (index * 97) % max(1, int(rect.width()))
        y = (index * 53 + shift * 3) % max(1, int(rect.height()))
        painter.drawLine(QPointF(rect.left() + x, rect.top() + y), QPointF(rect.left() + x - 3, rect.top() + y + 8))
