"""
FrontEngine's stylesheet and palette, built from ``tokens.py``.

This replaces qt-material. Every control the pages use gets an explicit rule, so
nothing falls back to a native look in the middle of a page, and the window's
QPalette carries the same colours for widgets that paint themselves (the pet
home, previews, colour swatches).

Colours never appear here as literals: everything comes from the light or dark
token set, so the two themes cannot drift apart. Indicator images (check mark,
arrows) are small SVGs shipped in ``icons/``.

``apply_app_style(window, theme)`` styles one top-level window and everything
parented to it. Overlays are separate top-level windows and keep their own look.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict

from PySide6.QtGui import QColor, QGuiApplication, QPalette
from PySide6.QtCore import Qt

from frontengine.ui.style.tokens import (CONTROL_HEIGHT, DEFAULT_THEME, FONT_SECTION, FONT_SIZE, FONT_SMALL,
                                         FONT_TITLE, RADIUS, RADIUS_CARD, RADIUS_SMALL, palette_for,
                                         resolve_theme)
from frontengine.utils.logging.loggin_instance import front_engine_logger

ICONS = Path(__file__).resolve().parent / "icons"

__all__ = ["DEFAULT_THEME", "apply_app_style", "build_stylesheet", "build_palette", "contrast_ratio",
           "contrast_text", "current_theme"]


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
    """The window frame: sidebar, brand, command search, page header and footer."""
    return f"""
QMainWindow, QDialog {{ background-color: {c['window']}; color: {c['text']}; }}
QWidget#navigationPanel {{ background-color: {c['sidebar']}; border-right: 1px solid {c['border']}; }}
QLabel#appBrand {{ color: {c['text']}; font-size: 18px; font-weight: 700; padding: 2px 8px 6px 8px; }}
QPushButton#commandSearch {{
    color: {c['muted']}; background-color: {c['surface']}; border: 1px solid {c['border']};
    border-radius: {RADIUS}px; text-align: left; padding: 7px 12px; font-weight: 400;
}}
QPushButton#commandSearch:hover {{ border-color: {c['accent']}; color: {c['text']}; }}
QListWidget#navSidebar {{ background-color: {c['sidebar']}; border: none; outline: 0; padding: 0px; }}
QListWidget#navSidebar::item {{
    color: {c['muted']}; padding: 6px 10px; margin: 1px 0px; border: none; border-radius: {RADIUS}px;
}}
QListWidget#navSidebar::item:hover {{ background-color: {c['surface_alt']}; color: {c['text']}; }}
QListWidget#navSidebar::item:selected, QListWidget#navSidebar::item:selected:active,
QListWidget#navSidebar::item:selected:!active {{
    background-color: {c['accent_soft']}; color: {c['text']}; font-weight: 600;
}}
QListWidget#navSidebar::item:disabled {{
    color: {c['faint']}; background: transparent; padding: 14px 10px 4px 10px; font-size: 11px; font-weight: 700;
}}
QWidget#pageHeader {{ background-color: transparent; border: none; }}
QLabel#pageTitle {{ font-size: {FONT_TITLE}px; font-weight: 700; color: {c['text']}; }}
QLabel#pageSubtitle {{ font-size: {FONT_SIZE}px; color: {c['muted']}; }}
QWidget#pageFooter {{ background-color: {c['surface']}; border-top: 1px solid {c['border']}; }}
QLabel#pageStatus {{ color: {c['muted']}; }}
QStackedWidget#pageBody, QWidget#pageContent {{ background-color: {c['window']}; }}
QWidget[settingPage="true"] {{ background-color: {c['window']}; }}
QLabel#sectionHeader {{ color: {c['text']}; font-size: {FONT_SECTION}px; font-weight: 700; padding-top: 2px; }}
QWidget#settingSection {{
    background-color: {c['surface']}; border: 1px solid {c['border']}; border-radius: {RADIUS_CARD}px;
}}
QWidget#sectionContent, QWidget#inlineActions {{ background: transparent; border: none; }}
"""


def _button_rules(c: Dict[str, str]) -> str:
    return f"""
QPushButton, QToolButton#actionMenu {{
    color: {c['text']}; background-color: {c['surface_alt']}; border: 1px solid {c['border']};
    border-radius: {RADIUS}px; padding: 5px 14px; min-height: {CONTROL_HEIGHT - 12}px; font-weight: 500;
}}
QPushButton:hover, QToolButton#actionMenu:hover {{ border-color: {c['border_strong']}; }}
QPushButton:pressed, QToolButton#actionMenu:pressed {{ background-color: {c['border']}; }}
QPushButton:focus, QToolButton#actionMenu:focus {{ border-color: {c['accent']}; }}
QPushButton:checked {{ background-color: {c['accent_soft']}; border-color: {c['accent']}; }}
QPushButton:disabled, QToolButton#actionMenu:disabled {{
    color: {c['faint']}; background-color: transparent; border-color: {c['border']};
}}
QToolButton#actionMenu {{ padding-right: 24px; }}
QToolButton#actionMenu::menu-indicator {{
    image: {{arrow}}; subcontrol-origin: padding; subcontrol-position: center right; right: 8px;
}}
QPushButton#primaryAction {{
    background-color: {c['accent']}; color: {c['on_accent']}; border: 1px solid {c['accent']};
    font-weight: 700; padding: 8px 24px;
}}
QPushButton#primaryAction:hover {{ background-color: {c['accent_hover']}; border-color: {c['accent_hover']}; }}
QPushButton#primaryAction:pressed {{ background-color: {c['accent_pressed']}; }}
QPushButton#primaryAction:disabled {{
    background-color: {c['surface_alt']}; color: {c['faint']}; border-color: {c['border']};
}}
QPushButton#primaryAction[tone="danger"], QPushButton[tone="danger"] {{
    background-color: transparent; color: {c['danger']}; border: 1px solid {c['danger']}; font-weight: 600;
}}
QPushButton#primaryAction[tone="danger"]:hover, QPushButton[tone="danger"]:hover {{
    background-color: {c['danger_soft']};
}}
QToolButton {{ color: {c['text']}; background: transparent; border: none; border-radius: {RADIUS_SMALL}px;
    padding: 4px 6px; }}
QToolButton:hover {{ background-color: {c['surface_alt']}; }}
QToolButton#sectionToggle {{ color: {c['muted']}; font-size: {FONT_SMALL}px; padding: 2px 8px; }}
QToolButton#sectionToggle:hover, QToolButton#sectionToggle:focus {{
    color: {c['text']}; background-color: {c['accent_soft']};
}}
"""


def _input_rules(c: Dict[str, str], arrow_down: str, arrow_up: str) -> str:
    fields = "QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox, QDateTimeEdit, QTimeEdit, " \
             "QDateEdit, QKeySequenceEdit"
    return f"""
{fields} {{
    color: {c['text']}; background-color: {c['input']}; border: 1px solid {c['border']};
    border-radius: {RADIUS}px; padding: 4px 10px; min-height: {CONTROL_HEIGHT - 10}px;
    selection-background-color: {c['accent']}; selection-color: {c['on_accent']};
}}
QPlainTextEdit, QTextEdit {{ padding: 6px 8px; }}
QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover, QPlainTextEdit:hover,
QTextEdit:hover, QTimeEdit:hover, QDateTimeEdit:hover {{ border-color: {c['border_strong']}; }}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QPlainTextEdit:focus,
QTextEdit:focus, QTimeEdit:focus, QDateTimeEdit:focus, QKeySequenceEdit:focus {{ border-color: {c['accent']}; }}
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled, QPlainTextEdit:disabled,
QTextEdit:disabled, QTimeEdit:disabled, QDateTimeEdit:disabled {{
    color: {c['faint']}; background-color: {c['surface_alt']}; border-color: {c['border']};
}}
QLineEdit[readOnly="true"] {{ background-color: {c['surface_alt']}; }}
QComboBox {{ padding-right: 28px; }}
QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: center right; width: 26px; border: none; }}
QComboBox::down-arrow {{ image: {arrow_down}; width: 12px; height: 12px; }}
QComboBox QAbstractItemView {{
    color: {c['text']}; background-color: {c['surface']}; border: 1px solid {c['border']};
    border-radius: {RADIUS}px; padding: 4px; outline: 0;
    selection-background-color: {c['accent_soft']}; selection-color: {c['text']};
}}
QSpinBox, QDoubleSpinBox, QTimeEdit, QDateTimeEdit, QDateEdit {{ padding-right: 22px; }}
QSpinBox::up-button, QDoubleSpinBox::up-button, QTimeEdit::up-button, QDateTimeEdit::up-button,
QDateEdit::up-button {{ subcontrol-origin: border; subcontrol-position: top right; width: 20px; border: none;
    background: transparent; }}
QSpinBox::down-button, QDoubleSpinBox::down-button, QTimeEdit::down-button, QDateTimeEdit::down-button,
QDateEdit::down-button {{ subcontrol-origin: border; subcontrol-position: bottom right; width: 20px; border: none;
    background: transparent; }}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow, QTimeEdit::up-arrow, QDateTimeEdit::up-arrow, QDateEdit::up-arrow {{
    image: {arrow_up}; width: 10px; height: 10px; }}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow, QTimeEdit::down-arrow, QDateTimeEdit::down-arrow,
QDateEdit::down-arrow {{ image: {arrow_down}; width: 10px; height: 10px; }}
"""


def _choice_rules(c: Dict[str, str]) -> str:
    """Check boxes, radio buttons, sliders and progress bars."""
    return f"""
QCheckBox, QRadioButton {{ color: {c['text']}; spacing: 8px; background: transparent; }}
QCheckBox:disabled, QRadioButton:disabled {{ color: {c['faint']}; }}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 16px; height: 16px; border: 1px solid {c['border_strong']}; background-color: {c['input']};
}}
QCheckBox::indicator {{ border-radius: 4px; }}
QRadioButton::indicator {{ border-radius: 9px; }}
QCheckBox::indicator:hover, QRadioButton::indicator:hover {{ border-color: {c['accent']}; }}
QCheckBox::indicator:checked {{ background-color: {c['accent']}; border-color: {c['accent']}; image: {_icon('check.svg')}; }}
QCheckBox::indicator:indeterminate {{
    background-color: {c['accent']}; border-color: {c['accent']}; image: {_icon('partial.svg')};
}}
QRadioButton::indicator:checked {{
    border-color: {c['accent']};
    background-color: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,
        stop:0 {c['on_accent']}, stop:0.32 {c['on_accent']}, stop:0.42 {c['accent']}, stop:1 {c['accent']});
}}
QCheckBox::indicator:disabled, QRadioButton::indicator:disabled {{
    background-color: {c['surface_alt']}; border-color: {c['border']};
}}
QCheckBox::indicator:checked:disabled {{ background-color: {c['border_strong']}; border-color: {c['border_strong']}; }}
QSlider {{ background: transparent; min-height: 22px; }}
QSlider::groove:horizontal {{ height: 4px; background: {c['border']}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {c['accent']}; border-radius: 2px; }}
QSlider::handle:horizontal {{
    width: 16px; height: 16px; margin: -7px 0px; border-radius: 9px;
    background: {c['surface']}; border: 2px solid {c['accent']};
}}
QSlider::handle:horizontal:hover {{ background: {c['accent_soft']}; }}
QSlider::groove:vertical {{ width: 4px; background: {c['border']}; border-radius: 2px; }}
QSlider::add-page:vertical {{ background: {c['accent']}; border-radius: 2px; }}
QSlider::handle:vertical {{
    width: 16px; height: 16px; margin: 0px -7px; border-radius: 9px;
    background: {c['surface']}; border: 2px solid {c['accent']};
}}
QSlider::sub-page:horizontal:disabled, QSlider::add-page:vertical:disabled {{ background: {c['border_strong']}; }}
QSlider::handle:disabled {{ border-color: {c['border_strong']}; }}
QProgressBar {{
    color: {c['text']}; background-color: {c['surface_alt']}; border: none; border-radius: 6px;
    text-align: center; min-height: 10px; font-size: {FONT_SMALL}px;
}}
QProgressBar::chunk {{ background-color: {c['accent']}; border-radius: 6px; }}
"""


def _container_rules(c: Dict[str, str]) -> str:
    """Tabs, item views, group boxes, menus, tool tips and scroll bars."""
    return f"""
QTabWidget::pane {{ border: 1px solid {c['border']}; border-radius: {RADIUS + 2}px; top: -1px;
    background-color: {c['surface']}; }}
QTabBar {{ background: transparent; }}
QTabBar::tab {{
    color: {c['muted']}; background: transparent; padding: 8px 14px; margin-right: 2px;
    border: none; border-bottom: 2px solid transparent;
}}
QTabBar::tab:hover {{ color: {c['text']}; }}
QTabBar::tab:selected {{ color: {c['text']}; border-bottom-color: {c['accent']}; font-weight: 600; }}
QTabWidget#sceneInspector QTabBar::tab {{ min-width: 54px; padding: 10px 8px; }}
QListView, QListWidget, QTreeView, QTreeWidget, QTableView, QTableWidget {{
    color: {c['text']}; background-color: {c['surface']}; alternate-background-color: {c['surface_alt']};
    border: 1px solid {c['border']}; border-radius: {RADIUS}px; outline: 0;
    selection-background-color: {c['accent_soft']}; selection-color: {c['text']};
}}
QListView::item, QListWidget::item, QTreeView::item, QTreeWidget::item {{ padding: 4px 6px; border-radius: 4px; }}
QListView::item:hover, QListWidget::item:hover, QTreeView::item:hover, QTreeWidget::item:hover {{
    background-color: {c['surface_alt']}; }}
QListView::item:selected, QListWidget::item:selected, QTreeView::item:selected, QTreeWidget::item:selected,
QTableView::item:selected, QTableWidget::item:selected {{ background-color: {c['accent_soft']}; color: {c['text']}; }}
QHeaderView::section {{
    color: {c['muted']}; background-color: {c['surface_alt']}; border: none;
    border-bottom: 1px solid {c['border']}; padding: 6px 8px; font-weight: 600;
}}
QTableCornerButton::section {{ background-color: {c['surface_alt']}; border: none; }}
QGroupBox {{
    color: {c['text']}; border: 1px solid {c['border']}; border-radius: {RADIUS + 2}px;
    margin-top: 14px; padding: 14px 10px 10px 10px; background-color: {c['surface']};
}}
QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0px 4px; color: {c['muted']};
    font-weight: 600; }}
QFrame[frameShape="4"], QFrame[frameShape="5"] {{ color: {c['border']}; }}
QSplitter::handle {{ background-color: {c['border']}; }}
QMenuBar {{ background-color: {c['window']}; color: {c['text']}; border-bottom: 1px solid {c['border']};
    padding: 2px 6px; }}
QMenuBar::item {{ background: transparent; padding: 6px 10px; border-radius: {RADIUS_SMALL}px; }}
QMenuBar::item:selected, QMenuBar::item:pressed {{ background-color: {c['surface_alt']}; }}
QMenu {{ color: {c['text']}; background-color: {c['surface']}; border: 1px solid {c['border']};
    border-radius: {RADIUS}px; padding: 6px; }}
QMenu::item {{ padding: 7px 28px 7px 12px; border-radius: {RADIUS_SMALL}px; }}
QMenu::item:selected {{ background-color: {c['accent_soft']}; color: {c['text']}; }}
QMenu::item:disabled {{ color: {c['faint']}; }}
QMenu::separator {{ height: 1px; background: {c['border']}; margin: 5px 8px; }}
QMenu::indicator {{ width: 14px; height: 14px; left: 6px; }}
QMenu::indicator:checked {{ image: {_icon('check.svg')}; background-color: {c['accent']}; border-radius: 3px; }}
QToolTip {{ color: {c['on_tooltip']}; background-color: {c['tooltip']}; border: none; border-radius: 6px;
    padding: 5px 8px; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget#pageContent {{ background-color: {c['window']}; }}
QScrollBar:vertical {{ width: 8px; background: transparent; margin: 2px 0px; }}
QScrollBar:horizontal {{ height: 8px; background: transparent; margin: 0px 2px; }}
QScrollBar::handle:vertical {{ background: {c['border_strong']}; border-radius: 4px; min-height: 28px; }}
QScrollBar::handle:horizontal {{ background: {c['border_strong']}; border-radius: 4px; min-width: 28px; }}
QScrollBar::handle:hover {{ background: {c['muted']}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0px; height: 0px; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
"""


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
            + _choice_rules(colors) + _container_rules(colors))


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


def apply_app_style(window, theme: str | None) -> None:
    """Style ``window`` and everything parented to it; replaces any previous stylesheet."""
    try:
        window.setPalette(build_palette(theme))
        window.setStyleSheet(build_stylesheet(theme))
    except Exception as error:  # pragma: no cover - a styling failure must not stop the app starting
        front_engine_logger.warning(f"[app_style] apply failed: {error!r}")
