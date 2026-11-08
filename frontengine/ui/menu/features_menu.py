"""The Features menu: every existing tool, grouped, one click from the Pet home.

The game is the main page now, so the tools live in a menu. Nothing here is a
second implementation: page entries select the existing page by its stable
ID, command entries run the existing ActionRegistry action, and the existing
Presets / Settings / Language / Help menus appear as submenus (the same QMenu
objects, so their actions and checked states are shared, not copied). Search,
recent and pinned entries come from the command palette's own history.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu

from frontengine.utils.multi_language.retranslate import retranslator, translate

if TYPE_CHECKING:
    from frontengine.ui.main_ui import FrontEngineMainUI

RECENT_LIMIT = 8


@dataclass(frozen=True)
class Entry:
    kind: str          # "page" (stable page ID), "action" (ActionRegistry ID) or "menu" (MainUI menu attribute)
    target: str


# (category label key, fallback, entries). Page IDs are the sidebar title keys.
CATEGORIES: tuple[tuple[str, str, tuple[Entry, ...]], ...] = (
    ("features_media", "Media and overlays", (
        Entry("page", "tab_video_text"), Entry("page", "tab_image_text"), Entry("page", "tab_web_text"),
        Entry("page", "tab_gif_text"), Entry("page", "tab_text_text"), Entry("page", "tab_sound_text"),
        Entry("page", "tab_particle_text"))),
    ("features_scene", "Scenes and wallpaper", (
        Entry("page", "tab_scene_text"), Entry("action", "scene_templates"), Entry("page", "tab_wallpaper_text"))),
    ("features_widgets", "Desktop widgets", (
        Entry("page", "tab_widgets_text"), Entry("action", "new_note"))),
    ("features_focus", "Focus and eye care", (
        Entry("page", "tab_focus_text"), Entry("page", "tab_screen_care_text"), Entry("action", "toggle_filter"))),
    ("features_presenting", "Presenting", (
        Entry("page", "tab_presentation_text"), Entry("action", "toggle_freeze"),
        Entry("action", "show_shortcuts"))),
    ("features_capture", "Capture and tools", (
        Entry("page", "tab_tools_text"), Entry("action", "capture_area"), Entry("action", "palette"),
        Entry("action", "move_window_next_monitor"))),
    ("features_pets", "Pets (advanced)", (Entry("page", "tab_pet_text"),)),
    ("features_automation", "Automation and integration", (Entry("menu", "settings_menu"),)),
    ("features_content", "Content, presets and Workshop", (
        Entry("menu", "preset_menu"), Entry("action", "workshop"))),
    ("features_control", "Overlay control", (
        Entry("page", "tab_control_center_text"), Entry("action", "show_all"), Entry("action", "hide_all"),
        Entry("action", "close_all"), Entry("action", "mute_all"), Entry("action", "toggle_lock"))),
    ("features_settings_help", "Settings and help", (
        Entry("menu", "language_menu"), Entry("menu", "help_menu"), Entry("menu", "how_to_menu"))),
)


def entry_label(ui: FrontEngineMainUI, entry: Entry) -> str:
    if entry.kind == "page":
        return ui.sidebar.page_label(ui.sidebar.page_index(entry.target))
    if entry.kind == "action":
        action = ui.action_registry.actions[entry.target]
        return translate(action.label_key, action.fallback)
    return getattr(ui, entry.target).title()


def open_page(ui: FrontEngineMainUI, page_id: str) -> bool:
    """Bring the window back on a page chosen by its stable ID."""
    ui.showNormal()
    ui.raise_()
    ui.activateWindow()
    return ui.sidebar.select_page_id(page_id)


def run_entry(ui: FrontEngineMainUI, entry: Entry) -> object:
    """Run through the shared registry IDs, so menu use shows up in Recent like the palette's."""
    identifier = "page." + entry.target if entry.kind == "page" else entry.target
    registry = ui.action_registry
    if identifier in registry.actions:
        ui.command_history.record(identifier, set(registry.actions))
    if entry.kind == "page":
        return open_page(ui, entry.target)
    return registry.invoke(entry.target)


class FeaturesMenu(QMenu):
    """Rebuilt each time it opens, so labels, recents and pins are always current."""

    def __init__(self, ui: FrontEngineMainUI) -> None:
        super().__init__(translate("features_menu", "Features"), ui.menu_bar)
        retranslator.bind(self, "features_menu", "Features", "setTitle")
        self.ui = ui
        self.entries: dict[QAction, Entry] = {}
        self._own_menus: list[QMenu] = []
        self.aboutToShow.connect(self.rebuild)
        retranslator.bind_call(self.rebuild)
        self.rebuild()

    def _new_submenu(self, title: str) -> QMenu:
        submenu = self.addMenu(title)
        self._own_menus.append(submenu)
        return submenu

    def rebuild(self) -> None:
        """Recreate the tree; old submenus are detached at once so none linger with stale text."""
        self.clear()
        self.entries.clear()
        for submenu in self._own_menus:
            submenu.setParent(None)
            submenu.deleteLater()
        self._own_menus.clear()
        # The application-wide Ctrl+K action already exists; a second shortcut would be ambiguous.
        self.addAction(translate("features_search", "Search features… (Ctrl+K)"), self.ui.open_command_palette)
        self._history_menu("features_pinned", "Pinned", "favorites")
        self._history_menu("features_recent", "Recent", "recent")
        self.addSeparator()
        for key, fallback, entries in CATEGORIES:
            submenu = self._new_submenu(translate(key, fallback))
            for entry in entries:
                self._add_entry(submenu, entry)
        plugins = sorted(getattr(self.ui, "plugin_pages", {}) or {})
        if plugins:                                   # whatever plugins registered this session
            submenu = self._new_submenu(translate("nav_group_extensions", "Extensions"))
            for name in plugins:
                self._add_entry(submenu, Entry("page", f"plugin:{name}"))

    def _add_entry(self, menu: QMenu, entry: Entry) -> None:
        if entry.kind == "menu":
            existing = getattr(self.ui, entry.target, None)
            if existing is not None:
                menu.addAction(existing.menuAction())
            return
        if entry.kind == "page" and self.ui.sidebar.page_index(entry.target) is None:
            return
        if entry.kind == "action" and entry.target not in self.ui.action_registry.actions:
            return
        action = menu.addAction(entry_label(self.ui, entry), lambda e=entry: run_entry(self.ui, e))
        self.entries[action] = entry

    def _history_menu(self, key: str, fallback: str, history_key: str) -> None:
        registry = self.ui.action_registry
        identifiers = self.ui.command_history.values(history_key, set(registry.actions))[:RECENT_LIMIT]
        submenu = self._new_submenu(translate(key, fallback))
        submenu.setEnabled(bool(identifiers))
        for identifier in identifiers:
            action = registry.actions[identifier]
            submenu.addAction(translate(action.label_key, action.fallback),
                              lambda i=identifier: registry.invoke(i))


def build_features_menu(ui: FrontEngineMainUI) -> FeaturesMenu:
    """Put Features first in the menu bar."""
    menu = FeaturesMenu(ui)
    actions = ui.menu_bar.actions()
    if actions:
        ui.menu_bar.insertMenu(actions[0], menu)
    else:
        ui.menu_bar.addMenu(menu)
    ui.features_menu = menu
    return menu
