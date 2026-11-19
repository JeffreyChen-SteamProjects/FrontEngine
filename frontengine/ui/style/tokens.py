"""
FrontEngine's own design tokens: two palettes and one spacing / type scale.

Two looks share each palette. The tool pages are quiet: neutral greys, thin
borders and small radii, close to a native Windows tool, with the INKSIDE
orange used sparingly. The pet pages (``ink_*`` tokens, applied to widgets
under ``inkStyle``) follow the built-in INKSIDE art instead - warm paper, even
ink outlines and rounder corners, in a rounded typeface - so the window and the
pets it shows read as one thing. Text on the orange accent is ink, not white:
ink on that orange passes WCAG AA, white does not.

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
    # Tool pages: quiet neutrals.
    "window": "#F5F5F4",          # page background
    "sidebar": "#EDEDEB",
    "surface": "#FFFFFF",         # cards, inputs' surroundings
    "surface_alt": "#F0F0EE",     # hover, alternate rows, secondary buttons
    "input": "#FFFFFF",
    "border": "#E1E1DF",
    "border_strong": "#C2C2BF",
    "text": "#1B1B1B",
    "muted": "#5C5C5A",
    "faint": "#8C8C89",
    "accent": "#F56A24",          # INKSIDE orange
    "accent_hover": "#FF7E3C",
    "accent_pressed": "#D9561A",
    "accent_soft": "#FCE3D3",     # selected rows, focus halo
    "on_accent": "#171715",
    "danger": "#B9382A",
    "danger_soft": "#F6DCD6",
    "success": "#3D8A4C",
    "tooltip": "#1B1B1B",
    "on_tooltip": "#FFFFFF",
    # Pet pages: INKSIDE ink on warm paper.
    "ink_window": "#F4EEDF",      # paper
    "ink_surface": "#FFFDF6",     # cards and controls
    "ink_surface_alt": "#EFE6D2", # pressed, hover
    "ink_line": "#171715",        # outlines
    "ink_text": "#171715",        # INKSIDE ink
    "ink_muted": "#5E584C",
    "ink_selected_text": "#FFFDF6",   # text on a selected (ink-filled) tab
}

DARK: Dict[str, str] = {
    "window": "#1C1C1C",
    "sidebar": "#171717",
    "surface": "#242424",
    "surface_alt": "#2D2D2D",
    "input": "#1F1F1F",
    "border": "#383838",
    "border_strong": "#555555",
    "text": "#F2F2F0",
    "muted": "#ABABA8",
    "faint": "#7A7A78",
    "accent": "#FF7A33",
    "accent_hover": "#FF915A",
    "accent_pressed": "#E8621C",
    "accent_soft": "#3D2A1F",
    "on_accent": "#171715",
    "danger": "#E2705F",
    "danger_soft": "#3E2522",
    "success": "#7CC08A",
    "tooltip": "#F2F2F0",
    "on_tooltip": "#1B1B1B",
    # Pet pages at night: paper-coloured lines on dark ink.
    "ink_window": "#1F1C17",
    "ink_surface": "#2A2620",
    "ink_surface_alt": "#353028",
    "ink_line": "#F3EEE3",        # INKSIDE paper
    "ink_text": "#F3EEE3",
    "ink_muted": "#BFB6A6",
    "ink_selected_text": "#1F1C17",
}

PALETTES = {"light": LIGHT, "dark": DARK}

# One spacing and type scale for every page (pixels).
RADIUS = 6
RADIUS_SMALL = 4
RADIUS_CARD = 8
# The pet pages' ink look: ink outlines, rounder corners and the bundled rounded typeface.
INK_LINE = 2
INK_RADIUS = 10
INK_RADIUS_CARD = 14
# jf open huninn (粉圓, SIL OFL 1.1): rounded, and it covers every character of the Traditional
# Chinese interface. It lacks much of Simplified Chinese, so that language keeps the system font
# rather than mixing two typefaces in one line.
INK_FONT = "jf-openhuninn-2.1"
INK_FONT_SKIPPED_FOR = ("Simplified_Chinese",)
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
