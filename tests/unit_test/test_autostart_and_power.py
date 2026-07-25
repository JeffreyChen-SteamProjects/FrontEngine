"""
開機自動啟動與省電模式的測試：產生的設定內容是純函式，可在任何平台驗證；
實際寫入只在本平台檢查開關能來回切換且不丟例外。

Tests for autostart and low-power mode. The generated configuration is pure and
checked on any platform; the real write is only exercised as an enable/disable
round trip that must never raise.
"""
import sys

from frontengine.utils.autostart.autostart_service import (
    APP_NAME, autostart_path, desktop_entry_text, is_enabled, launch_agent_plist, launch_command,
    quote_command, set_enabled,
)
from frontengine.utils.power_mode.power_mode import (
    LOW_POWER_CEILING_MS, LOW_POWER_FACTOR, scaled_interval,
)


# --- command building -----------------------------------------------------
def test_launch_command_uses_this_interpreter() -> None:
    command = launch_command()
    assert command[0] == sys.executable
    assert command[1:] == ["-m", "frontengine"] or getattr(sys, "frozen", False)


def test_quote_command_quotes_paths_with_spaces() -> None:
    assert quote_command(["C:\\Program Files\\py.exe", "-m", "frontengine"]) == \
        '"C:\\Program Files\\py.exe" -m frontengine'
    assert quote_command(["/usr/bin/python3", "-m", "frontengine"]) == "/usr/bin/python3 -m frontengine"


# --- generated configuration ---------------------------------------------
def test_desktop_entry_is_a_valid_autostart_entry() -> None:
    entry = desktop_entry_text(["/usr/bin/python3", "-m", "frontengine"])
    assert entry.startswith("[Desktop Entry]")
    assert "Type=Application" in entry
    assert f"Name={APP_NAME}" in entry
    assert "Exec=/usr/bin/python3 -m frontengine" in entry
    assert "X-GNOME-Autostart-enabled=true" in entry


def test_launch_agent_plist_lists_every_argument() -> None:
    plist = launch_agent_plist(["/usr/bin/python3", "-m", "frontengine"])
    assert plist.startswith("<?xml")
    assert "<key>RunAtLoad</key>" in plist
    assert "<string>/usr/bin/python3</string>" in plist
    assert "<string>-m</string>" in plist
    assert "<string>frontengine</string>" in plist


def test_launch_agent_plist_escapes_xml() -> None:
    plist = launch_agent_plist(["/opt/a&b/python"], label="com.test<x>")
    assert "&amp;" in plist and "&lt;x&gt;" in plist
    assert "a&b" not in plist


# --- platform paths -------------------------------------------------------
def test_autostart_path_matches_the_platform() -> None:
    path = autostart_path()
    if sys.platform == "win32":
        assert path is None, "Windows uses the registry, not a file"
    elif sys.platform == "darwin":
        assert path is not None and path.suffix == ".plist"
    else:
        assert path is not None and path.name.endswith(".desktop")


def test_enabling_and_disabling_round_trips() -> None:
    original = is_enabled()
    try:
        if set_enabled(True):
            assert is_enabled() is True
        if set_enabled(False):
            assert is_enabled() is False
    finally:
        set_enabled(original)


# --- low power ------------------------------------------------------------
def test_normal_mode_keeps_the_base_interval() -> None:
    assert scaled_interval(33, False) == 33
    assert scaled_interval(1000, False) == 1000


def test_low_power_slows_updates_down() -> None:
    assert scaled_interval(33, True) == 33 * LOW_POWER_FACTOR
    assert scaled_interval(33, True) > 33


def test_low_power_is_capped_so_it_stays_usable() -> None:
    assert scaled_interval(200, True) <= max(200, LOW_POWER_CEILING_MS)
    assert scaled_interval(1000, True) == 1000, "an already-slow timer is left alone"


def test_low_power_tolerates_bad_input() -> None:
    assert scaled_interval("junk", True) > 0
    assert scaled_interval(None, False) > 0
    assert scaled_interval(0, False) >= 1
