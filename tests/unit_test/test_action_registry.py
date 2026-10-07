"""Action dispatch preserves existing side effects without invoking real devices."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from frontengine.ui.main_ui import FrontEngineMainUI
from frontengine.utils.actions.action_registry import Action, ActionRegistry
from frontengine.user_setting.user_setting_file import default_hotkeys


def test_registry_rejects_unknown_duplicate_and_missing_values():
    registry, calls = ActionRegistry(), []
    action = Action("preset", "label", "Preset", calls.append, True)
    registry.register(action)
    assert not registry.execute("__getattribute__")
    assert not registry.execute("preset", " ")
    assert registry.execute("preset", "Work")
    assert calls == ["Work"]
    with pytest.raises(ValueError):
        registry.register(action)


def test_main_bindings_preserve_all_hotkey_and_rule_routes(monkeypatch):
    import frontengine.ui.main_ui as module
    controls = SimpleNamespace(**{name: Mock() for name in (
        "clear_all", "hide_all", "show_all", "toggle_mute_all", "step_opacity_all",
        "toggle_lock_all", "set_quality_tier")})
    window = SimpleNamespace(control_center_ui=controls,
                             web_setting_ui=SimpleNamespace(show_next_dashboard_page=Mock()),
                             presentation_setting_ui=SimpleNamespace(toggle_freeze=Mock()),
                             toggle_shortcut_sheet=Mock())
    media, monitor, preset = Mock(), Mock(), Mock()
    monkeypatch.setattr(module, "send_media_key", media)
    monkeypatch.setattr(module, "move_to_next_monitor", monitor)
    monkeypatch.setattr(module, "apply_named_preset", preset)
    window.action_registry = FrontEngineMainUI._build_action_registry(window)
    assert set(default_hotkeys) <= set(window.action_registry.actions)
    for action in default_hotkeys:
        FrontEngineMainUI._handle_hotkey(window, action)
    assert controls.step_opacity_all.call_args_list[0].args == (0.1,)
    assert controls.step_opacity_all.call_args_list[1].args == (-0.1,)
    assert [call.args[0] for call in media.call_args_list] == [
        "media_play_pause", "media_next", "media_previous"]
    monitor.assert_called_once_with()
    FrontEngineMainUI._on_rule_fired(window, {"action": "apply_preset", "value": "Work"})
    preset.assert_called_once_with(window, "Work")
    FrontEngineMainUI._on_rule_fired(window, {"action": "quality_tier", "value": "low"})
    controls.set_quality_tier.assert_called_once_with("low")
    FrontEngineMainUI._handle_hotkey(window, "unregistered")
