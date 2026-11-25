"""
FrontEngine's own design tokens: two palettes and one spacing / type scale.

The look is an animator's cel desk. FrontEngine stacks layers over the desktop
the way cels are stacked over a background, so the window borrows that desk: a
light table with a non-photo-blue field guide, cards drawn as stacked cels with
an ink outline, a peg bar across the top of every page, and a dark rack of index
tabs on the left. Each sidebar group has its own spot ink (``spot_*``), which
colours its peg bar, its tabs and the sheet behind its cards; the INKSIDE orange
stays the colour of the one primary action.

The pet pages (``ink_*`` tokens, applied to widgets under ``inkStyle``) keep the
warm paper of the built-in INKSIDE art, so the window and the pets it shows read
as one thing. Text on the orange accent is ink, not white: ink on that orange
passes WCAG AA, white does not.

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
    # The light table and the cels on it.
    "window": "#E9EFF1",          # page background: the table
    "field": "#BBD8E4",           # non-photo blue: the field guide printed on it
    "surface": "#FDFEFE",         # cards, inputs' surroundings
    "surface_alt": "#EDF2F4",     # hover, alternate rows, secondary buttons
    "input": "#FFFFFF",
    "line": "#1B1F22",            # the ink outline of cels, tabs and the peg bar
    "border": "#C6D2D7",
    "border_strong": "#8497A0",
    "text": "#14181B",
    "muted": "#4A575E",
    "faint": "#77868D",
    "accent": "#F56A24",          # INKSIDE orange
    "accent_hover": "#FF7E3C",
    "accent_pressed": "#D9561A",
    "accent_soft": "#FCE3D3",     # selected rows, focus halo
    "on_accent": "#171715",
    "danger": "#B9382A",
    "danger_soft": "#F6DCD6",
    "success": "#2F7F45",
    "tooltip": "#1B1F22",
    "on_tooltip": "#FFFFFF",
    # The rack of index tabs; dark in both themes.
    "rail": "#1B1F22",
    "rail_hover": "#2C3338",
    "rail_text": "#F1F5F6",
    "rail_muted": "#A9B8BF",
    # One spot ink per sidebar group.
    "spot_home": "#F56A24",
    "spot_screen": "#3FA7D6",
    "spot_desktop": "#59B36E",
    "spot_work": "#9A7BE0",
    "spot_control": "#E6B52C",
    "spot_other": "#93A4AC",
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
    "window": "#16191C",
    "field": "#25333A",
    "surface": "#1F2428",
    "surface_alt": "#2A3136",
    "input": "#191D20",
    "line": "#7F9099",
    "border": "#374147",
    "border_strong": "#566570",
    "text": "#F0F3F4",
    "muted": "#A9B5BA",
    "faint": "#75838A",
    "accent": "#FF7A33",
    "accent_hover": "#FF915A",
    "accent_pressed": "#E8621C",
    "accent_soft": "#3D2A1F",
    "on_accent": "#171715",
    "danger": "#E2705F",
    "danger_soft": "#3E2522",
    "success": "#7CC08A",
    "tooltip": "#F0F3F4",
    "on_tooltip": "#16191C",
    "rail": "#0E1113",
    "rail_hover": "#20272B",
    "rail_text": "#EDF1F2",
    "rail_muted": "#93A2A9",
    "spot_home": "#FF7A33",
    "spot_screen": "#3E9CC7",
    "spot_desktop": "#4FA364",
    "spot_work": "#8E70D6",
    "spot_control": "#CFA024",
    "spot_other": "#788A93",
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

# Sidebar group key -> its spot ink. Unknown groups (plugins) use spot_other.
GROUP_SPOTS = {"nav_group_home": "spot_home", "nav_group_on_screen": "spot_screen",
               "nav_group_desktop": "spot_desktop", "nav_group_work": "spot_work",
               "nav_group_control": "spot_control"}
DEFAULT_SPOT = "spot_other"

# One spacing and type scale for every page (pixels).
RADIUS = 7
RADIUS_SMALL = 5
RADIUS_CARD = 12
CEL_LINE = 2            # the outline of a cel
CEL_OFFSET = 5          # how far the sheet behind a cel shows
PEG_BAR_HEIGHT = 20
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
