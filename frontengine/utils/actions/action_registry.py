"""Explicit action IDs, translated labels and callbacks shared by input routes."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


ACTION_LABELS = {
    "close_all": ("control_center_close_all", "Close all"),
    "hide_all": ("control_center_hide_all", "Hide all"),
    "show_all": ("control_center_show_all", "Show all"),
    "mute_all": ("control_center_mute_all", "Mute all"),
    "opacity_up": ("hotkey_opacity_up", "Opacity up"),
    "opacity_down": ("hotkey_opacity_down", "Opacity down"),
    "dashboard_next": ("web_dashboard_next", "Next page"),
    "toggle_lock": ("hotkey_toggle_lock", "Lock / unlock overlays"),
    "show_shortcuts": ("hotkey_show_shortcuts", "Show this shortcut list"),
    "toggle_freeze": ("hotkey_toggle_freeze", "Freeze / unfreeze the screen"),
    "media_play_pause": ("hotkey_media_play_pause", "Play / pause media"),
    "media_next": ("hotkey_media_next", "Next track"),
    "media_previous": ("hotkey_media_previous", "Previous track"),
    "move_window_next_monitor": ("hotkey_move_window_next_monitor", "Move window to the next monitor"),
    "apply_preset": ("rules_action_apply_preset", "Apply preset"),
    "quality_tier": ("rules_action_quality", "Set quality"),
    "scene_load": ("rules_action_scene_load", "Load scene"),
    "scene_start": ("rules_action_scene_start", "Play scene"),
    "scene_stop": ("rules_action_scene_stop", "Stop scene"),
    "layer_show": ("rules_action_layer_show", "Show layer"),
    "layer_hide": ("rules_action_layer_hide", "Hide layer"),
    "layer_opacity": ("rules_action_layer_opacity", "Set layer opacity"),
    "layer_position": ("rules_action_layer_position", "Move layer"),
}


@dataclass(frozen=True)
class Action:
    """One stable identifier; callbacks are invoked only through the registry."""

    identifier: str
    label_key: str
    fallback: str
    callback: Callable[[str], object]
    takes_value: bool = False
    optional_value: bool = False


class ActionRegistry:
    """Dispatch registered actions without evaluating names or resolving attributes."""

    def __init__(self) -> None:
        self.actions: dict[str, Action] = {}

    def register(self, action: Action) -> None:
        """Reject duplicate IDs so extensions cannot silently replace actions."""
        if not action.identifier or action.identifier in self.actions:
            raise ValueError("Duplicate or empty action identifier")
        self.actions[action.identifier] = action

    def bind(self, identifier: str, callback: Callable[[str], object], takes_value: bool = False,
             *, optional_value: bool = False) -> None:
        """Bind a built-in definition to its owning application instance."""
        key, fallback = ACTION_LABELS[identifier]
        self.register(Action(identifier, key, fallback, callback, takes_value, optional_value))

    def execute(self, identifier: str, value: str = "") -> bool:
        """Return False for unknown/missing input or an explicitly failed callback."""
        return self.invoke(identifier, value) is not False

    def invoke(self, identifier: str, value: str = "") -> object:
        """Return the callback receipt so async callers can observe completion."""
        action = self.actions.get(identifier)
        if action is None or (action.takes_value and not action.optional_value and not value.strip()):
            return False
        return action.callback(value)
