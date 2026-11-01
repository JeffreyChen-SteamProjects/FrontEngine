"""
FrontEngine's own design tokens: two palettes and one spacing / type scale.

The colours follow the built-in INKSIDE art - ink black, warm paper and one
orange - so the window and the pets it shows read as one thing. Text on the
orange accent is ink, not white: ink on that orange passes WCAG AA, white does
not.

Theme names: ``light``, ``dark`` and ``system`` (follow the operating system).
Settings written by earlier versions hold qt-material file names such as
``dark_amber.xml``; ``resolve_theme`` maps those onto light or dark instead of
failing.
"""
from __future__ import annotations

from typing import Dict, Optional

THEMES = ("system", "light", "dark")
DEFAULT_THEME = "system"

LIGHT: Dict[str, str] = {
    "window": "#F6F1E7",          # page background: warm paper
    "sidebar": "#EEE7D8",
    "surface": "#FFFDF8",         # cards, inputs' surroundings
    "surface_alt": "#F1EBDF",     # hover, alternate rows, secondary buttons
    "input": "#FFFFFF",
    "border": "#DDD3C1",
    "border_strong": "#BDB09A",
    "text": "#171715",            # INKSIDE ink
    "muted": "#6A6458",
    "faint": "#9A9284",
    "accent": "#F56A24",          # INKSIDE orange
    "accent_hover": "#FF7E3C",
    "accent_pressed": "#D9561A",
    "accent_soft": "#FCE3D3",     # selected rows, focus halo
    "on_accent": "#171715",
    "danger": "#B9382A",
    "danger_soft": "#F6DCD6",
    "success": "#3D8A4C",
    "tooltip": "#171715",
    "on_tooltip": "#FFFDF8",
}

DARK: Dict[str, str] = {
    "window": "#171614",
    "sidebar": "#12110F",
    "surface": "#211F1C",
    "surface_alt": "#2B2925",
    "input": "#1A1917",
    "border": "#38352F",
    "border_strong": "#565148",
    "text": "#F3EEE3",            # INKSIDE paper
    "muted": "#AAA294",
    "faint": "#7A7368",
    "accent": "#FF7A33",
    "accent_hover": "#FF915A",
    "accent_pressed": "#E8621C",
    "accent_soft": "#3D2A1F",
    "on_accent": "#171715",
    "danger": "#E2705F",
    "danger_soft": "#3E2522",
    "success": "#7CC08A",
    "tooltip": "#F3EEE3",
    "on_tooltip": "#171715",
}

PALETTES = {"light": LIGHT, "dark": DARK}

# One spacing and type scale for every page (pixels).
RADIUS = 8
RADIUS_SMALL = 6
RADIUS_CARD = 12
CONTROL_HEIGHT = 32
FONT_SIZE = 13
FONT_SMALL = 12
FONT_TITLE = 24
FONT_SECTION = 14


def resolve_theme(name: Optional[str], system_dark: bool = False) -> str:
    """``light`` or ``dark`` for a stored theme name, including legacy qt-material file names."""
    value = (name or DEFAULT_THEME).strip().lower() if isinstance(name, str) else DEFAULT_THEME
    if value in ("light", "dark"):
        return value
    if value.endswith(".xml"):                  # qt-material: light_blue.xml, dark_amber.xml, ...
        return "light" if value.startswith("light") else "dark"
    return "dark" if system_dark else "light"


def normalise_theme(name: Optional[str]) -> str:
    """The stored form: one of THEMES; legacy names become the light or dark they looked like."""
    if isinstance(name, str) and name.strip().lower() in THEMES:
        return name.strip().lower()
    if isinstance(name, str) and name.strip().lower().endswith(".xml"):
        return resolve_theme(name)
    return DEFAULT_THEME


def palette_for(theme: str) -> Dict[str, str]:
    """The colour tokens of a resolved theme (``light`` or ``dark``)."""
    return PALETTES.get(theme, LIGHT)
