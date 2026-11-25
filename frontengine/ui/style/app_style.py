"""
FrontEngine's stylesheet and palette, built from ``tokens.py``.

This replaces qt-material. Every control the pages use gets an explicit rule, so
nothing falls back to a native look in the middle of a page, and the window's
QPalette carries the same colours for widgets that paint themselves (the pet
home, previews, colour swatches).

Colours never appear here as literals: everything comes from the light or dark
token set, so the two themes cannot drift apart. Indicator images (check mark,
arrows, switches) are small SVGs shipped in ``icons/``. The glass panels and the
picture behind them are painted by ``glass.py`` and ``backdrop.py``; containers stay
transparent here so they show through.

``apply_app_style(window, theme)`` styles one top-level window and everything
parented to it. Overlays are separate top-level windows and keep their own look.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict

from PySide6.QtGui import QColor, QGuiApplication, QPalette
from PySide6.QtCore import Qt

from frontengine.ui.style.glass import THEME_PROPERTY
from frontengine.ui.style.tokens import (CONTROL_HEIGHT, DEFAULT_THEME, FONT_SECTION, FONT_SIZE, FONT_SMALL,
                                         FONT_TITLE, INK_FONT, INK_FONT_SKIPPED_FOR, RADIUS, RADIUS_FIELD,
                                         RADIUS_SMALL, palette_for, resolve_theme)
from frontengine.utils.logging.loggin_instance import front_engine_logger

ICONS = Path(__file__).resolve().parent / "icons"
FONTS = Path(__file__).resolve().parent / "fonts"       # jf open huninn (SIL OFL 1.1), for the pet pages

__all__ = ["DEFAULT_THEME", "apply_app_style", "build_stylesheet", "build_palette", "contrast_ratio",
           "contrast_text", "current_theme", "load_brand_fonts", "mark_ink", "use_brand_font"]


def _rgb(color: str) -> tuple[int, int, int]:
    value = (color or "").lstrip("#")
    if len(value) != 6:
        return (128, 128, 128)
    try:
        return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))
    except ValueError:
        return (128, 128, 128)


def relative_luminance(color: str) -> float:
    """WCAG 2 relative luminance of ``#rrggbb``."""
    def channel(value: int) -> float:
        value /= 255.0
        return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
    red, green, blue = (channel(value) for value in _rgb(color))
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(first: str, second: str) -> float:
    """WCAG 2 contrast ratio between two colours (1 to 21)."""
    lighter, darker = sorted((relative_luminance(first), relative_luminance(second)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def contrast_text(background: str) -> str:
    """Black or white, whichever has the higher contrast on ``background``."""
    return "#000000" if contrast_ratio(background, "#000000") >= contrast_ratio(background, "#ffffff") else "#ffffff"


def _icon(name: str) -> str:
    """A shipped icon as a stylesheet url(); forward slashes so Windows paths survive."""
    return f"url({(ICONS / name).as_posix()})"


def system_is_dark() -> bool:
    """Whether the operating system asks for a dark appearance (False when unknown)."""
    application = QGuiApplication.instance()
    if application is None:
        return False
    try:
        return application.styleHints().colorScheme() == Qt.ColorScheme.Dark
    except AttributeError:                       # Qt before 6.5
        return False


def current_theme(name: str | None) -> str:
    """``light`` or ``dark`` for a stored theme name, asking the system for ``system``."""
    return resolve_theme(name, system_dark=system_is_dark())


def _shell_rules(c: Dict[str, str]) -> str:
    """The window frame: navigation, command search, page header, footer and status bar."""
    return f"""
QMainWindow, QDialog {{ background-color: {c['window']}; color: {c['text']}; }}
QWidget#navigationPanel, QWidget#navInset, QWidget#brandMark, QWidget#overlayStatus {{
    background: transparent; border: none; }}
QLabel#appBrand {{ color: {c['text']}; font-size: 18px; font-weight: 600; }}
QPushButton#commandSearch, QPushButton#foldButton {{
    color: {c['muted']}; background-color: {c['well']}; border: 1px solid {c['well_edge']};
    border-radius: 17px; text-align: left; padding: 0px; font-weight: 400; min-height: 32px;
}}
QPushButton#foldButton {{ background-color: transparent; border-color: transparent; }}
QPushButton#commandSearch:hover, QPushButton#foldButton:hover {{ background-color: {c['glass_hover']}; }}
QPushButton#commandSearch:focus, QPushButton#foldButton:focus {{ border-color: {c['accent_line']}; }}
QLabel#commandSearchCaption, QLabel#foldCaption {{ color: {c['muted']}; }}
QLabel#shortcutHint {{
    color: {c['muted']}; font-size: 11px; border: 1px solid {c['well_edge']}; border-radius: 8px;
    padding: 0px 6px;
}}
QListWidget#navSidebar {{ background: transparent; border: none; outline: 0; padding: 0px; }}
QListWidget#navSidebar::item {{ background: transparent; border: none; padding: 0px; margin: 0px; }}
QListWidget#navSidebar QScrollBar:vertical {{ width: 5px; margin: 0px; }}
QListWidget#navSidebar QScrollBar::handle:vertical {{ background: {c['well_edge']}; border-radius: 2px; }}
QWidget#pageHeader, QWidget#pageFooter {{ background: transparent; border: none; }}
QLabel#pageTitle {{ font-size: {FONT_TITLE}px; font-weight: 300; color: {c['text']}; }}
QLabel#pageSubtitle {{ font-size: {FONT_SIZE}px; color: {c['muted']}; }}
QLabel#pageStatus, QLabel#statusText {{ color: {c['muted']}; }}
QPushButton#statusAction {{ background: transparent; border: 1px solid transparent; color: {c['text']};
    padding: 1px 12px; min-height: 22px; border-radius: 12px; font-weight: 500; }}
QPushButton#statusAction:hover {{ background-color: {c['glass_hover']}; }}
QPushButton#statusAction:focus {{ border-color: {c['accent_line']}; }}
QPushButton#statusAction:disabled {{ color: {c['faint']}; background: transparent; }}
QStackedWidget, QWidget#pageContent, QWidget[settingPage="true"] {{ background: transparent; }}
QLabel#sectionHeader {{ color: {c['text']}; font-size: {FONT_SECTION}px; font-weight: 600; }}
QWidget#settingSection {{ background: transparent; border: none; }}
QLabel#sectionNote {{ color: {c['muted']}; }}
QWidget#sectionContent, QWidget#inlineActions, QWidget#pageColumn {{ background: transparent; border: none; }}
QLabel#homeStatus {{ font-size: 15px; font-weight: 600; color: {c['text']}; }}
QTabWidget#homeTabs::pane {{ border: none; background: transparent; top: 0px; }}
QTabWidget#homeTabs > QTabBar::tab {{ padding: 9px 16px; font-size: {FONT_SIZE}px; }}
QWidget#homeTabPage, QWidget#emptyHome {{ background: transparent; }}
"""


def _button_rules(c: Dict[str, str]) -> str:
    return f"""
QPushButton, QToolButton#actionMenu {{
    color: {c['text']}; background-color: {c['glass_nested']}; border: 1px solid {c['well_edge']};
    border-radius: {RADIUS}px; padding: 5px 16px; min-height: {CONTROL_HEIGHT - 12}px; font-weight: 500;
}}
QPushButton:hover, QToolButton#actionMenu:hover {{ background-color: {c['glass_hover']}; }}
QPushButton:pressed, QToolButton#actionMenu:pressed {{ background-color: {c['well']}; }}
QPushButton:focus, QToolButton#actionMenu:focus {{ border-color: {c['accent_line']}; }}
QPushButton:checked {{ background-color: {c['pill']}; color: {c['on_pill']}; border-color: {c['pill']}; }}
QPushButton:disabled, QToolButton#actionMenu:disabled {{
    color: {c['faint']}; background-color: transparent; border-color: {c['well_edge']};
}}
QToolButton#actionMenu {{ padding-right: 26px; max-height: {CONTROL_HEIGHT - 12}px; }}
QToolButton#actionMenu::menu-indicator {{
    image: {{arrow}}; subcontrol-origin: padding; subcontrol-position: center right; right: 10px;
}}
QPushButton#primaryAction {{
    background-color: {c['accent']}; color: {c['on_accent']}; border: 1px solid {c['accent']};
    border-radius: 18px; font-weight: 600; padding: 7px 26px;
}}
QPushButton#primaryAction:hover {{ background-color: {c['accent_hover']}; border-color: {c['accent_hover']}; }}
QPushButton#primaryAction:focus {{ border-color: {c['text']}; }}
QPushButton#primaryAction:pressed {{ background-color: {c['accent_pressed']}; }}
QPushButton#primaryAction:disabled {{
    background-color: transparent; color: {c['faint']}; border-color: {c['well_edge']};
}}
QDialogButtonBox QPushButton:default {{
    background-color: {c['accent']}; color: {c['on_accent']}; border: 1px solid {c['accent']}; font-weight: 600;
}}
QDialogButtonBox QPushButton:default:hover {{ background-color: {c['accent_hover']}; border-color: {c['accent_hover']}; }}
QDialogButtonBox QPushButton:default:disabled {{
    background-color: transparent; color: {c['faint']}; border-color: {c['well_edge']};
}}
QPushButton#primaryAction[tone="danger"], QPushButton[tone="danger"] {{
    background-color: {c['glass_nested']}; color: {c['danger']}; border: 1px solid {c['danger']}; font-weight: 600;
}}
QPushButton#primaryAction[tone="danger"]:hover, QPushButton[tone="danger"]:hover {{
    background-color: {c['danger_soft']};
}}
QToolButton {{ color: {c['text']}; background: transparent; border: none; border-radius: {RADIUS_SMALL}px;
    padding: 4px 6px; }}
QToolButton:hover {{ background-color: {c['glass_hover']}; }}
QToolButton#sectionToggle {{ color: {c['muted']}; font-size: {FONT_SMALL}px; padding: 3px 8px; }}
QToolButton#sectionToggle:hover, QToolButton#sectionToggle:focus {{
    color: {c['text']}; background-color: {c['glass_hover']};
}}
"""


def _input_rules(c: Dict[str, str], arrow_down: str, arrow_up: str) -> str:
    fields = "QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox, QDateTimeEdit, QTimeEdit, " \
             "QDateEdit, QKeySequenceEdit"
    return f"""
{fields} {{
    color: {c['text']}; background-color: {c['well']}; border: 1px solid {c['well_edge']};
    border-radius: {RADIUS}px; padding: 4px 12px; min-height: {CONTROL_HEIGHT - 10}px;
    selection-background-color: {c['accent']}; selection-color: {c['on_accent']};
}}
QPlainTextEdit, QTextEdit {{ padding: 8px 10px; border-radius: {RADIUS_FIELD}px; }}
QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover, QPlainTextEdit:hover,
QTextEdit:hover, QTimeEdit:hover, QDateTimeEdit:hover {{ border-color: {c['border_strong']}; }}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QPlainTextEdit:focus,
QTextEdit:focus, QTimeEdit:focus, QDateTimeEdit:focus, QKeySequenceEdit:focus {{ border-color: {c['accent_line']}; }}
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled, QPlainTextEdit:disabled,
QTextEdit:disabled, QTimeEdit:disabled, QDateTimeEdit:disabled {{
    color: {c['faint']}; background-color: transparent;
}}
QLineEdit[readOnly="true"] {{ background-color: transparent; }}
QComboBox {{ padding-right: 30px; }}
QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: center right; width: 30px; border: none; }}
QComboBox::down-arrow {{ image: {arrow_down}; width: 12px; height: 12px; }}
QComboBox QAbstractItemView {{
    color: {c['text']}; background-color: {c['surface']}; border: 1px solid {c['border']};
    border-radius: {RADIUS_SMALL}px; padding: 4px; outline: 0;
    selection-background-color: {c['accent_soft']}; selection-color: {c['text']};
}}
QSpinBox, QDoubleSpinBox, QTimeEdit, QDateTimeEdit, QDateEdit {{ padding-right: 24px; }}
QSpinBox::up-button, QDoubleSpinBox::up-button, QTimeEdit::up-button, QDateTimeEdit::up-button,
QDateEdit::up-button {{ subcontrol-origin: border; subcontrol-position: top right; width: 24px; border: none;
    background: transparent; }}
QSpinBox::down-button, QDoubleSpinBox::down-button, QTimeEdit::down-button, QDateTimeEdit::down-button,
QDateEdit::down-button {{ subcontrol-origin: border; subcontrol-position: bottom right; width: 24px; border: none;
    background: transparent; }}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow, QTimeEdit::up-arrow, QDateTimeEdit::up-arrow, QDateEdit::up-arrow {{
    image: {arrow_up}; width: 10px; height: 10px; }}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow, QTimeEdit::down-arrow, QDateTimeEdit::down-arrow,
QDateEdit::down-arrow {{ image: {arrow_down}; width: 10px; height: 10px; }}
"""


def _switch(state: str, theme: str) -> str:
    return _icon(f"switch-{state}-{theme}.svg")


def _choice_rules(c: Dict[str, str], theme: str) -> str:
    """Switches (check boxes), radio buttons, sliders and progress bars."""
    return f"""
QCheckBox, QRadioButton {{ color: {c['text']}; spacing: 8px; background: transparent; }}
QCheckBox:disabled, QRadioButton:disabled {{ color: {c['faint']}; }}
QCheckBox::indicator {{ width: 34px; height: 20px; border: none; background: transparent;
    image: {_switch('off', theme)}; }}
QCheckBox::indicator:checked {{ image: {_switch('on', theme)}; }}
QCheckBox::indicator:indeterminate {{ image: {_switch('mixed', theme)}; }}
QCheckBox::indicator:disabled {{ image: {_switch('off-disabled', theme)}; }}
QCheckBox::indicator:checked:disabled {{ image: {_switch('on-disabled', theme)}; }}
QCheckBox:focus {{ color: {c['accent_line']}; }}
QRadioButton::indicator {{
    width: 16px; height: 16px; border: 1px solid {c['border_strong']}; border-radius: 9px;
    background-color: {c['well']};
}}
QRadioButton::indicator:hover {{ border-color: {c['accent']}; }}
QRadioButton::indicator:checked {{
    border-color: {c['accent']};
    background-color: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,
        stop:0 {c['on_accent']}, stop:0.32 {c['on_accent']}, stop:0.42 {c['accent']}, stop:1 {c['accent']});
}}
QRadioButton::indicator:disabled {{ background-color: transparent; border-color: {c['border']}; }}
QSlider {{ background: transparent; min-height: 22px; }}
QSlider::groove:horizontal {{ height: 6px; background: {c['well_edge']}; border-radius: 3px; }}
QSlider::sub-page:horizontal {{ background: {c['accent_line']}; border-radius: 3px; }}
QSlider::handle:horizontal {{
    width: 18px; height: 18px; margin: -6px 0px; border-radius: 9px;
    background: {c['knob']}; border: none;
}}
QSlider::handle:horizontal:hover, QSlider::handle:horizontal:focus {{ background: {c['accent']}; }}
QSlider::groove:vertical {{ width: 6px; background: {c['well_edge']}; border-radius: 3px; }}
QSlider::add-page:vertical {{ background: {c['accent_line']}; border-radius: 3px; }}
QSlider::handle:vertical {{
    width: 18px; height: 18px; margin: 0px -6px; border-radius: 9px;
    background: {c['knob']}; border: none;
}}
QSlider::sub-page:horizontal:disabled, QSlider::add-page:vertical:disabled {{ background: {c['border_strong']}; }}
QProgressBar {{
    color: {c['text']}; background-color: {c['well']}; border: none; border-radius: 6px;
    text-align: center; min-height: 12px; font-size: {FONT_SMALL}px;
}}
QProgressBar::chunk {{ background-color: {c['accent']}; border-radius: 6px; }}
"""


def _container_rules(c: Dict[str, str]) -> str:
    """Tabs, item views, group boxes, menus, tool tips and scroll bars."""
    return f"""
QTabWidget::pane {{ border: 1px solid {c['glass_edge_low']}; border-radius: {RADIUS_FIELD}px; top: 4px;
    background-color: {c['glass_nested']}; }}
QTabBar {{ background: transparent; }}
QTabBar::tab {{
    color: {c['muted']}; background: transparent; padding: 6px 16px; margin: 0px 4px 8px 0px;
    border: 1px solid transparent; border-radius: {RADIUS}px;
}}
QTabBar::tab:hover {{ color: {c['text']}; background: {c['glass_hover']}; }}
QTabBar::tab:selected {{ color: {c['on_pill']}; background: {c['pill']}; font-weight: 600; }}
QTabBar::tab:focus {{ border-color: {c['accent_line']}; }}
QTabWidget#sceneInspector QTabBar::tab {{ min-width: 46px; padding: 6px 10px; }}
QListView, QListWidget, QTreeView, QTreeWidget, QTableView, QTableWidget {{
    color: {c['text']}; background-color: {c['well']}; alternate-background-color: {c['glass_nested']};
    border: 1px solid {c['well_edge']}; border-radius: {RADIUS_FIELD}px; outline: 0; padding: 4px;
    selection-background-color: {c['accent_soft']}; selection-color: {c['text']};
}}
QListView:focus, QListWidget:focus, QTreeView:focus, QTreeWidget:focus,
QTableView:focus, QTableWidget:focus {{ border-color: {c['accent_line']}; }}
QListView::item, QListWidget::item, QTreeView::item, QTreeWidget::item {{ padding: 4px 8px;
    border-radius: {RADIUS_SMALL}px; }}
QListView::item:hover, QListWidget::item:hover, QTreeView::item:hover, QTreeWidget::item:hover {{
    background-color: {c['glass_hover']}; }}
QListView::item:selected, QListWidget::item:selected, QTreeView::item:selected, QTreeWidget::item:selected,
QTableView::item:selected, QTableWidget::item:selected {{ background-color: {c['accent_soft']}; color: {c['text']}; }}
QHeaderView {{ background: transparent; }}
QHeaderView::section {{
    color: {c['muted']}; background-color: {c['surface_alt']}; border: none;
    border-bottom: 1px solid {c['border']}; padding: 6px 8px; font-weight: 600;
}}
QTableCornerButton::section {{ background-color: {c['surface_alt']}; border: none; }}
QGroupBox {{
    color: {c['text']}; border: 1px solid {c['glass_edge_low']}; border-radius: {RADIUS_FIELD}px;
    margin-top: 14px; padding: 14px 10px 10px 10px; background-color: {c['glass_nested']};
}}
QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0px 4px; color: {c['muted']};
    font-weight: 600; }}
QFrame[frameShape="4"], QFrame[frameShape="5"] {{ color: {c['border']}; }}
QSplitter::handle {{ background: transparent; }}
QSplitter::handle:hover {{ background-color: {c['glass_hover']}; }}
QMenuBar {{ background: transparent; color: {c['text']}; border: none; padding: 4px 10px; }}
QMenuBar::item {{ background: transparent; padding: 6px 12px; border-radius: 13px; }}
QMenuBar::item:selected, QMenuBar::item:pressed {{ background-color: {c['glass_hover']}; }}
QMenu {{ color: {c['text']}; background-color: {c['surface']}; border: 1px solid {c['border']};
    border-radius: {RADIUS_SMALL}px; padding: 6px; }}
QMenu::item {{ padding: 7px 28px 7px 12px; border-radius: {RADIUS_SMALL - 3}px; }}
QMenu::item:selected {{ background-color: {c['accent_soft']}; color: {c['text']}; }}
QMenu::item:disabled {{ color: {c['faint']}; }}
QMenu::separator {{ height: 1px; background: {c['border']}; margin: 5px 8px; }}
QMenu::indicator {{ width: 14px; height: 14px; left: 6px; }}
QMenu::indicator:checked {{ image: {_icon('check.svg')}; background-color: {c['accent']}; border-radius: 3px; }}
QToolTip {{ color: {c['on_tooltip']}; background-color: {c['tooltip']}; border: none; border-radius: 6px;
    padding: 5px 8px; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollBar:vertical {{ width: 8px; background: transparent; margin: 2px 0px; }}
QScrollBar:horizontal {{ height: 8px; background: transparent; margin: 0px 2px; }}
QScrollBar::handle:vertical {{ background: {c['border_strong']}; border-radius: 4px; min-height: 28px; }}
QScrollBar::handle:horizontal {{ background: {c['border_strong']}; border-radius: 4px; min-width: 28px; }}
QScrollBar::handle:hover {{ background: {c['muted']}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0px; height: 0px; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
QAbstractScrollArea::corner {{ background: transparent; border: none; }}
"""


INK = 'QWidget[inkStyle="true"]'        # the pet pages and their dialogs; see ``mark_ink``


def _ink_rules(c: Dict[str, str]) -> str:
    """The pet pages: the rounded typeface reads better a little heavier."""
    return f"""
{INK} {{ background: transparent; }}
QDialog[inkStyle="true"] {{ background-color: {c['window']}; }}
{INK} QLabel#pageTitle {{ font-weight: 600; }}
{INK} QLabel#sectionHeader {{ font-size: {FONT_SECTION + 1}px; font-weight: 700; }}
{INK} QPushButton, {INK} QToolButton#actionMenu {{ font-weight: 600; }}
"""


def mark_ink(widget) -> None:
    """Give a pet page or dialog its own look: warm glass panels, and the rounded typeface for it
    and its children while the language is one the typeface covers.

    A plain QWidget subclass paints a stylesheet background only with WA_StyledBackground, so
    without it the strip behind the page title stayed the tools' grey above the paper. The
    typeface is set as the widget's font rather than in the stylesheet, so a language switch
    changes just that font instead of rebuilding the whole stylesheet (which resized windows)."""
    widget.setProperty("inkStyle", True)
    widget.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    use_brand_font(widget)


def use_brand_font(widget) -> None:
    """Draw the widget (a heading, or a pet page and everything on it) in the rounded typeface
    while the language is one it covers."""
    from frontengine.utils.multi_language.retranslate import retranslator
    load_brand_fonts()
    helper = _InkFont(widget)
    widget._ink_font = helper                 # held by the widget; the retranslator holds it weakly
    helper.refresh()
    retranslator.bind_call(helper.refresh)


class _InkFont:
    """Keeps one marked widget's typeface in step with the interface language."""

    def __init__(self, widget) -> None:
        import weakref
        self._widget = weakref.ref(widget)
        self.base = list(widget.font().families())

    def refresh(self) -> None:
        from frontengine.utils.multi_language.language_wrapper import language_wrapper
        widget = self._widget()
        if widget is None:
            return
        font = widget.font()
        if language_wrapper.language in INK_FONT_SKIPPED_FOR:
            font.setFamilies(self.base)
        else:                                  # missing glyphs (⌂, ♥) fall back to the usual font
            font.setFamilies([INK_FONT, *[family for family in self.base if family != INK_FONT]])
        widget.setFont(font)


_FONTS_LOADED = False


def load_brand_fonts() -> list[str]:
    """Register the bundled rounded typeface once; returns the families Qt now knows from it."""
    global _FONTS_LOADED
    from PySide6.QtGui import QFontDatabase
    families: list[str] = []
    if _FONTS_LOADED or QGuiApplication.instance() is None:
        return families
    _FONTS_LOADED = True
    for path in sorted(FONTS.glob("*.ttf")):
        identifier = QFontDatabase.addApplicationFont(str(path))
        if identifier < 0:
            front_engine_logger.warning(f"[app_style] could not load font {path.name}")
            continue
        families.extend(QFontDatabase.applicationFontFamilies(identifier))
    return families


def build_stylesheet(theme: str | None) -> str:
    """The whole stylesheet for a stored theme name (``system``, ``light``, ``dark`` or a legacy name)."""
    resolved = current_theme(theme)
    colors = palette_for(resolved)
    arrow_down, arrow_up = _icon(f"arrow-down-{resolved}.svg"), _icon(f"arrow-up-{resolved}.svg")
    base = f"""
QWidget {{ color: {colors['text']}; font-size: {FONT_SIZE}px; }}
QLabel {{ background: transparent; }}
QLabel:disabled {{ color: {colors['faint']}; }}
"""
    buttons = _button_rules(colors).replace("{arrow}", arrow_down)
    return (base + _shell_rules(colors) + buttons + _input_rules(colors, arrow_down, arrow_up)
            + _choice_rules(colors, resolved) + _container_rules(colors)
            + _ink_rules(colors))


def build_palette(theme: str | None) -> QPalette:
    """The same colours as a QPalette, for widgets that paint themselves."""
    c = palette_for(current_theme(theme))
    palette = QPalette()
    roles = {
        QPalette.ColorRole.Window: c["window"], QPalette.ColorRole.WindowText: c["text"],
        QPalette.ColorRole.Base: c["input"], QPalette.ColorRole.AlternateBase: c["surface_alt"],
        QPalette.ColorRole.Text: c["text"], QPalette.ColorRole.Button: c["surface_alt"],
        QPalette.ColorRole.ButtonText: c["text"], QPalette.ColorRole.Highlight: c["accent"],
        QPalette.ColorRole.HighlightedText: c["on_accent"], QPalette.ColorRole.ToolTipBase: c["tooltip"],
        QPalette.ColorRole.ToolTipText: c["on_tooltip"], QPalette.ColorRole.PlaceholderText: c["faint"],
        QPalette.ColorRole.Link: c["accent"], QPalette.ColorRole.Mid: c["border"],
        QPalette.ColorRole.Midlight: c["surface_alt"], QPalette.ColorRole.Dark: c["border_strong"],
        QPalette.ColorRole.Light: c["surface"], QPalette.ColorRole.BrightText: c["danger"],
    }
    for role, color in roles.items():
        palette.setColor(role, QColor(color))
    for role in (QPalette.ColorRole.WindowText, QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(c["faint"]))
    return palette


def apply_app_style(window, theme: str | None, application: bool = False) -> None:
    """Style ``window`` and everything parented to it; replaces any previous stylesheet.

    With ``application`` the palette also becomes the application's. Widgets under a
    stylesheet take the roles the sheet does not set (base, mid, highlight) from the
    application palette, not the window's, so self-painted views such as the pet home
    would otherwise paint the platform's white base inside a dark window.
    """
    try:
        load_brand_fonts()
        palette = build_palette(theme)
        window.setProperty(THEME_PROPERTY, current_theme(theme))
        if application and QGuiApplication.instance() is not None:
            QGuiApplication.setPalette(palette)
        window.setPalette(palette)
        window.setStyleSheet(build_stylesheet(theme))
    except Exception as error:  # pragma: no cover - a styling failure must not stop the app starting
        front_engine_logger.warning(f"[app_style] apply failed: {error!r}")
