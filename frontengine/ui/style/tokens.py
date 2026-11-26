"""
FrontEngine's own design tokens: two palettes and one spacing / type scale.

The look is layered glass. FrontEngine floats things over the desktop, and its own
window does the same: the desktop wallpaper, blurred, lies at the back
(``backdrop.py``), and the navigation, every section and the status bar are
translucent sheets above it (``glass.py``), told apart by depth instead of colour.
One warm accent marks the main action. Colours with an alpha are ``#AARRGGBB``;
``window``, ``surface`` and ``input`` stay solid for dialogs, menus and widgets that
paint themselves.

The pet pages (widgets under ``inkStyle``) use the same glass with a warm tint and a
rounded typeface.

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
    "backdrop": "#E9F1F4",        # what the wallpaper is pulled towards
    "glow_cool": "#C6E4E6",       # the built-in dawn
    "glow_mid": "#D3E1F2",
    "glow_warm": "#FFDCBC",
    "window": "#E9F1F4",          # dialogs
    "surface": "#FBFDFE",         # menus, lists that pop up
    "surface_alt": "#EDF3F6",
    "input": "#FFFFFF",
    "glass": "#A6FFFFFF",         # a panel
    "glass_warm": "#A6FFF6EC",    # a panel on a pet page
    "glass_nested": "#73FFFFFF",  # a panel inside a panel
    "glass_hover": "#80FFFFFF",
    "glass_edge": "#F2FFFFFF",    # the lit upper edge
    "glass_edge_low": "#59FFFFFF",
    "well": "#9EFFFFFF",          # inputs and lists, sunk into a panel
    "well_edge": "#3312303E",
    "shadow": "#3A173644",
    "pill": "#12303E",            # the selected page
    "on_pill": "#FFFFFF",
    "knob": "#FFFFFF",            # slider handles
    "border": "#C3D2D9",
    "border_strong": "#7D929C",
    "text": "#10222B",
    "muted": "#33464F",
    "faint": "#526872",
    "accent": "#F3A660",
    "accent_hover": "#F8B97E",
    "accent_pressed": "#E39249",
    "accent_line": "#B2560F",     # focus rings and slider tracks, where the accent itself is too pale
    "accent_soft": "#FBE3CB",
    "on_accent": "#33210F",
    "danger": "#A82E20",
    "danger_soft": "#F6DCD6",
    "success": "#1F6634",
    "tooltip": "#12303E",
    "on_tooltip": "#FFFFFF",
}

DARK: Dict[str, str] = {
    "backdrop": "#0C2531",
    "glow_cool": "#175B66",
    "glow_mid": "#1E4259",
    "glow_warm": "#6E5244",
    "window": "#102A36",
    "surface": "#173542",
    "surface_alt": "#1F4150",
    "input": "#0F2833",
    "glass": "#1AFFFFFF",
    "glass_warm": "#1CFFE9D2",
    "glass_nested": "#10FFFFFF",
    "glass_hover": "#26FFFFFF",
    "glass_edge": "#52FFFFFF",
    "glass_edge_low": "#1AFFFFFF",
    "well": "#3D000C12",
    "well_edge": "#38FFFFFF",
    "shadow": "#66000000",
    "pill": "#F4F8FA",
    "on_pill": "#12303E",
    "knob": "#F4F8FA",
    "border": "#3B5A68",
    "border_strong": "#6C8A97",
    "text": "#F4F8FA",
    "muted": "#DCE6EB",
    "faint": "#A3B8C2",
    "accent": "#FFC691",
    "accent_hover": "#FFD5AE",
    "accent_pressed": "#F0B078",
    "accent_line": "#FFC691",
    "accent_soft": "#45504F",
    "on_accent": "#33210F",
    "danger": "#FFCBC3",
    "danger_soft": "#5A3A3B",
    "success": "#B4F0CB",
    "tooltip": "#F4F8FA",
    "on_tooltip": "#12303E",
}

PALETTES = {"light": LIGHT, "dark": DARK}

# How much of the wallpaper's own colour shows; the rest is the theme's tint.
BACKDROP_MIX = {"light": .34, "dark": .42}

# One spacing and type scale for every page (pixels).
RADIUS = 15             # pills: controls are about 34 px tall
RADIUS_SMALL = 10
RADIUS_FIELD = 14       # controls of more than one line
RADIUS_CARD = 22
RADIUS_NESTED = 16
SHADOW_DEPTH = 10       # how far below a panel its shadow reaches
# jf open huninn (粉圓, SIL OFL 1.1): rounded, and it covers every character of the Traditional
# Chinese interface. It lacks much of Simplified Chinese, so that language keeps the system font
# rather than mixing two typefaces in one line.
INK_FONT = "jf-openhuninn-2.1"
INK_FONT_SKIPPED_FOR = ("Simplified_Chinese",)
CONTROL_HEIGHT = 32
FONT_SIZE = 13
FONT_SMALL = 12
FONT_TITLE = 30
FONT_SECTION = 16


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
