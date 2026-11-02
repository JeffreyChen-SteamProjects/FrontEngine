"""Theme colours and the sky. Themes change looks only; layout, paths and items never change."""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPen

from frontengine.utils.pet_game.environment import daylight, season, sky, weather

PALETTES = {
    "warm_home": {"floor": (150, 120, 90), "day": (250, 232, 205), "night": (42, 38, 70)},
    "green_studio": {"floor": (104, 136, 88), "day": (222, 240, 214), "night": (28, 50, 44)},
    "night_studio": {"floor": (92, 92, 132), "day": (216, 216, 240), "night": (18, 18, 44)},
}
WEATHER_GLYPHS = {"clear": "☀", "cloudy": "☁", "rain": "☂", "snow": "❄"}
NIGHT_GLYPH = "☾"
NIGHT_TINT = QColor(28, 34, 78)
MAX_NIGHT_SHADE = 70           # alpha at midnight: pieces stay easy to read
DUSK_DAYLIGHT = 0.6            # the tint starts as daylight falls below this
RAIN_DROPS = 60


# Content pack themes, already checked by content_pack: id -> palette, and id -> built-in base.
PACK_PALETTES: dict[str, dict] = {}
PACK_BASES: dict[str, str] = {}


def register_themes(themes) -> None:
    """Make content pack themes drawable; a theme whose pack is gone falls back to the warm home."""
    for theme in themes:
        PACK_PALETTES[theme.identifier] = {"floor": theme.floor, "day": theme.day, "night": theme.night}
        PACK_BASES[theme.identifier] = theme.base


def base_theme(theme: str) -> str:
    """The built-in theme whose furniture pictures a theme uses."""
    return theme if theme in PALETTES else PACK_BASES.get(theme, "warm_home")


def palette(theme: str) -> dict:
    return PALETTES.get(theme) or PACK_PALETTES.get(theme) or PALETTES["warm_home"]


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


def night_shade(time_ms: int) -> int:
    """Alpha for the evening tint on the desktop strip: 0 by day, up to MAX_NIGHT_SHADE at midnight."""
    dark = max(0.0, DUSK_DAYLIGHT - daylight(time_ms)) / DUSK_DAYLIGHT
    return round(dark * MAX_NIGHT_SHADE)


def glyph(home: str, time_ms: int) -> str:
    """A tiny weather / night sign for the desktop button."""
    if sky(time_ms) == "night" and weather(home, time_ms) == "clear":
        return NIGHT_GLYPH
    return WEATHER_GLYPHS[weather(home, time_ms)]


# A light touch of the season in the sky: petals, nothing in summer, leaves, then snow.
SEASON_SPECKS = {"spring": QColor(244, 170, 196, 170), "autumn": QColor(214, 128, 52, 170),
                 "winter": QColor(250, 250, 255, 200)}
SPECKS = 18


def _paint_season(painter: QPainter, rect: QRectF, time_ms: int, moving: bool, snowing: bool) -> None:
    color = SEASON_SPECKS.get(season(time_ms))
    if color is None:
        return
    count = SPECKS * (3 if snowing else 1)
    drift = (time_ms // 80) % 200 if moving else 0          # reduced motion keeps them still
    painter.save()
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(color)
    width, height = max(1, int(rect.width())), max(1, int(rect.height()))
    for index in range(count):
        x = (index * 131 + drift) % width
        y = (index * 71 + drift * 2) % height
        size = 2.5 if index % 3 else 3.5
        painter.drawEllipse(QPointF(rect.left() + x, rect.top() + y), size, size * 0.7)
    painter.restore()


def paint_sky(painter: QPainter, rect: QRectF, theme: str, home: str, time_ms: int, moving: bool) -> None:
    """The overview's background: time-of-day colour and, when it rains, slanted drops."""
    current = weather(home, time_ms)
    top = sky_color(theme, time_ms, current != "clear")
    gradient = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    gradient.setColorAt(0, top)
    gradient.setColorAt(1, top.lighter(115))
    painter.fillRect(rect, gradient)
    _paint_season(painter, rect, time_ms, moving, current == "snow")
    if current != "rain":
        return
    painter.setPen(QPen(QColor(120, 150, 200, 150), 1))
    shift = (time_ms // 50) % 40 if moving else 0          # reduced motion keeps the drops still
    for index in range(RAIN_DROPS):
        x = (index * 97) % max(1, int(rect.width()))
        y = (index * 53 + shift * 3) % max(1, int(rect.height()))
        painter.drawLine(QPointF(rect.left() + x, rect.top() + y), QPointF(rect.left() + x - 3, rect.top() + y + 8))
