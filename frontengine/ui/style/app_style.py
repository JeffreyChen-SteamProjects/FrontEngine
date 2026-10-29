"""
疊在 qt-material 之上的樣式：側邊欄、頁首、分區標題、主要動作按鈕。

顏色一律從目前主題的色票算出來，不寫死。這個程式有排程日夜主題，寫死顏色的話
淺色主題會變成白底白字。對比色（選取列上的文字要黑還是白）用亮度算，而不是憑
印象挑一個。

qt_material 的 apply_stylesheet() 是把樣式表整份寫到視窗上，所以每次套用主題之
後都要再接一次這裡的樣式，否則會被蓋掉。

Styling layered on top of qt-material: the sidebar, page headers, section
headings and the primary action button.

Colours are derived from the active theme's palette rather than hard-coded. This
application schedules a day/night theme, so hard-coded colours would leave white
text on white in the light one. Which contrast colour a selected row needs is
computed from luminance instead of guessed.

qt_material's apply_stylesheet() writes a whole stylesheet onto the window, so
this has to be appended again after every theme change or it is simply lost.
"""
from __future__ import annotations

from typing import Dict

from frontengine.utils.logging.loggin_instance import front_engine_logger

DEFAULT_THEME = "dark_amber.xml"

# 主題色票缺鍵時的後備值，這樣壞掉的主題名稱不會讓樣式整份消失。
# Fallbacks for a missing palette entry, so a bad theme name cannot make the
# whole stylesheet vanish.
_FALLBACK_PALETTE = {
    "primaryColor": "#ffd740",
    "primaryLightColor": "#ffff74",
    "secondaryColor": "#232629",
    "secondaryLightColor": "#4f5b62",
    "secondaryDarkColor": "#31363b",
    "primaryTextColor": "#ffffff",
    "secondaryTextColor": "#ffffff",
}


def _to_rgb(color: str) -> tuple[int, int, int]:
    """把 #rrggbb 轉成 (r, g, b)；認不得的值當成中灰。"""
    value = (color or "").lstrip("#")
    if len(value) != 6:
        return (128, 128, 128)
    try:
        return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))
    except ValueError:
        return (128, 128, 128)


def _luminance(color: str) -> float:
    """相對亮度（0 到 1），用來決定疊在上面的文字該用黑還是白。"""
    red, green, blue = _to_rgb(color)
    return (0.299 * red + 0.587 * green + 0.114 * blue) / 255.0


def contrast_text(background: str) -> str:
    """在指定底色上讀得清楚的文字顏色。"""
    return "#000000" if _luminance(background) > 0.55 else "#ffffff"


def _rgba(color: str, alpha: float) -> str:
    """半透明版本的顏色，用來做低調的說明文字與分隔線。"""
    red, green, blue = _to_rgb(color)
    return f"rgba({red}, {green}, {blue}, {alpha:.2f})"


def load_palette(theme: str) -> Dict[str, str]:
    """讀取主題色票，任何失敗都退回後備值而不是讓呼叫端爆掉。"""
    palette = dict(_FALLBACK_PALETTE)
    try:
        from qt_material import get_theme

        loaded = get_theme(theme or DEFAULT_THEME)
        if isinstance(loaded, dict):
            palette.update({key: value for key, value in loaded.items() if value})
    except Exception as error:  # pragma: no cover - 壞掉的主題名稱
        front_engine_logger.warning(f"[app_style] palette load failed: {error!r}")
    return palette


def build_stylesheet(theme: str) -> str:
    """依目前主題組出這個程式自己的樣式表。"""
    palette = load_palette(theme)
    primary = palette["primaryColor"]
    surface = palette["secondaryColor"]
    surface_dark = palette["secondaryDarkColor"]
    surface_light = palette["secondaryLightColor"]
    text = palette["primaryTextColor"]
    on_primary = contrast_text(primary)
    card = surface_light if _luminance(surface) > 0.55 else _rgba(text, 0.035)
    muted = _rgba(text, 0.68)
    divider = _rgba(text, 0.10)

    return f"""
/* 側邊欄 / Sidebar */
QWidget#navigationPanel {{
    background-color: {surface_dark};
    border-right: 1px solid {divider};
}}
QLabel#appBrand {{
    color: {text};
    font-size: 19px;
    font-weight: bold;
    padding: 2px 8px 6px 8px;
}}
QPushButton#commandSearch {{
    text-transform: none;
    color: {muted};
    background-color: {_rgba(text, 0.05)};
    border: 1px solid {divider};
    border-radius: 8px;
    text-align: left;
    padding: 7px 12px;
    font-weight: normal;
}}
QPushButton#commandSearch:hover {{ border-color: {primary}; color: {text}; }}
QListWidget#navSidebar {{
    background-color: {surface_dark};
    border: none;
    outline: 0;
    padding: 0px;
}}
QListWidget#navSidebar::item {{
    color: {muted};
    padding: 6px 12px;
    margin: 2px 0px;
    border: none;
    border-radius: 8px;
}}
QListWidget#navSidebar::item:hover {{
    background-color: {_rgba(surface_light, 0.35)};
    color: {text};
}}
/* 選取列：兩種 active 狀態都要寫。只寫 :selected 的話會被 qt-material 更明確
   的規則蓋掉，文字顏色就跑掉了。
   Both active states are spelled out: a bare :selected loses to qt-material's
   more specific rule and the text colour goes with it. */
QListWidget#navSidebar::item:selected,
QListWidget#navSidebar::item:selected:active,
QListWidget#navSidebar::item:selected:!active {{
    background-color: {_rgba(primary, 0.13)};
    border: none;
    color: {primary};
    font-weight: bold;
}}
/* 群組標題：不可選取，比分頁列小且更淡 */
QListWidget#navSidebar::item:disabled {{
    color: {_rgba(text, 0.48)};
    background: transparent;
    border: none;
    padding: 12px 12px 4px 12px;
    font-size: 10px;
    font-weight: bold;
}}

/* 頁首與頁尾 / Page header and footer */
QWidget#pageHeader {{
    background-color: transparent;
    border: none;
}}
QLabel#pageTitle {{
    font-size: 26px;
    font-weight: bold;
    color: {text};
}}
QLabel#pageSubtitle {{
    font-size: 13px;
    color: {muted};
}}
QWidget#pageFooter {{
    background-color: {surface};
    border-top: 1px solid {divider};
}}
QLabel#pageStatus {{
    color: {muted};
}}

/* 分區標題 / Section headings */
QLabel#sectionHeader {{
    color: {text};
    font-size: 13px;
    font-weight: bold;
    padding-top: 2px;
}}

QWidget#settingSection {{
    background-color: {card};
    border: 1px solid {divider};
    border-radius: 12px;
}}
QWidget#sectionContent {{ background: transparent; border: none; }}
QWidget#inlineActions {{ background: transparent; border: none; }}
QWidget[settingPage="true"], QWidget#pageContent {{ background-color: {surface}; }}
QWidget[settingPage="true"] QSlider {{ background: transparent; }}
QWidget[settingPage="true"] QPushButton {{
    text-transform: none;
    background-color: {_rgba(text, 0.055)};
    color: {text};
    border: 1px solid {_rgba(text, 0.14)};
    border-radius: 8px;
    padding: 5px 14px;
    font-weight: normal;
}}
QWidget[settingPage="true"] QPushButton:hover {{
    background-color: {_rgba(primary, 0.10)};
    border-color: {_rgba(primary, 0.6)};
}}
QWidget[settingPage="true"] QPushButton:disabled {{
    color: {_rgba(text, 0.30)};
    background-color: transparent;
    border-color: {divider};
}}
QWidget[settingPage="true"] QPushButton:checked {{
    color: {primary};
    background-color: {_rgba(primary, 0.12)};
    border-color: {primary};
}}
QToolButton#actionMenu {{
    text-transform: none;
    color: {text};
    background-color: {_rgba(text, 0.055)};
    border: 1px solid {_rgba(text, 0.14)};
    border-radius: 8px;
    height: 24px;
    padding: 9px 18px 9px 12px;
    font-weight: normal;
}}
QToolButton#actionMenu:hover, QToolButton#actionMenu:focus {{
    background-color: {_rgba(primary, 0.10)};
    border-color: {primary};
}}
QToolButton#actionMenu::menu-indicator {{
    subcontrol-origin: padding;
    subcontrol-position: center right;
    right: 7px;
}}
QToolButton#sectionToggle {{
    text-transform: none;
    color: {muted};
    background: transparent;
    border: none;
    border-radius: 6px;
    height: 20px;
    padding: 2px 8px;
    font-size: 12px;
}}
QToolButton#sectionToggle:hover, QToolButton#sectionToggle:focus {{
    color: {primary};
    background-color: {_rgba(primary, 0.10)};
}}
QMenu {{
    border: 1px solid {_rgba(text, 0.18)};
    border-radius: 8px;
    padding: 6px;
}}
QMenu::item {{ padding: 8px 24px 8px 12px; border-radius: 5px; }}
QMenu::item:selected {{ background-color: {_rgba(primary, 0.15)}; color: {text}; }}
QTabWidget#sceneInspector::pane {{ border: 1px solid {divider}; border-radius: 10px; }}
QTabWidget#sceneInspector QTabBar::tab {{
    text-transform: none;
    min-width: 54px;
    padding: 10px 8px;
    font-weight: normal;
}}

/* 主要動作：和其他按鈕明顯不同 / The primary action stands apart */
QPushButton#primaryAction {{
    background-color: {primary};
    color: {on_primary};
    border: none;
    border-radius: 8px;
    font-weight: bold;
    padding: 9px 26px;
}}
QPushButton#primaryAction[tone="danger"] {{
    background: transparent;
    color: {text};
    border: 1px solid {_rgba(text, 0.24)};
    font-weight: normal;
}}
QPushButton#primaryAction[tone="danger"]:hover {{
    background-color: {_rgba(primary, 0.12)};
    border-color: {primary};
}}
QPushButton#primaryAction:hover {{
    background-color: {palette['primaryLightColor']};
}}
QPushButton#primaryAction:disabled {{
    background-color: {_rgba(surface_light, 0.5)};
    color: {muted};
}}

/* 內容區的捲軸不要搶注意力 */
QScrollArea {{ background: transparent; border: none; }}
QWidget#pageBody {{ background: {surface}; }}
QScrollBar:vertical {{ width: 6px; background: transparent; margin: 2px 0px; }}
QScrollBar:horizontal {{ height: 6px; background: transparent; margin: 0px 2px; }}
QScrollBar::handle:vertical {{
    background: {_rgba(text, 0.20)}; border-radius: 3px; min-height: 28px;
}}
QScrollBar::handle:horizontal {{
    background: {_rgba(text, 0.20)}; border-radius: 3px; min-width: 28px;
}}
QScrollBar::handle:hover {{ background: {_rgba(primary, 0.55)}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0px; height: 0px; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
"""


def apply_app_style(window, theme: str) -> None:
    """
    把這個程式的樣式接在 qt-material 產生的樣式表後面。
    一定要在 apply_stylesheet() 之後呼叫，順序反了就會被整份蓋掉。
    """
    try:
        window.setStyleSheet(window.styleSheet() + build_stylesheet(theme))
    except Exception as error:  # pragma: no cover - 樣式套用失敗不該讓程式起不來
        front_engine_logger.warning(f"[app_style] apply failed: {error!r}")
