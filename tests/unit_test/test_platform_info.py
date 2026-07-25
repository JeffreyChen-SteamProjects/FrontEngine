"""
跨平台系統偵測的測試：解析部分在任何平台都能驗證，實機讀取只檢查型別與範圍。
Cross-platform probe tests: the parsers run anywhere, while live reads are only
checked for shape and range.
"""
from frontengine.utils.platform_info.platform_info import (
    idle_seconds, parse_macos_battery, parse_macos_idle, parse_wmctrl_geometry, read_battery,
    read_linux_battery, run_command, standable_windows,
)

IOREG_SAMPLE = """
    | |   "HIDIdleTime" = 4500000000
    | |   "HIDPointerAcceleration" = 3145
"""
PMSET_SAMPLE = "Now drawing from 'Battery Power'\n -InternalBattery-0 (id=1234) 87%; discharging; 3:12 remaining"
PMSET_AC = "Now drawing from 'AC Power'\n -InternalBattery-0 (id=1234) 100%; charged; 0:00 remaining"
WMCTRL_SAMPLE = (
    "0x03000007  0 100  200  800  600  host Editor\n"
    "0x03000008  0 0    0    40   20   host Tiny\n"
    "0x03000009  0 900  50   640  480  host Browser\n"
)


# --- macOS idle -----------------------------------------------------------
def test_macos_idle_is_nanoseconds() -> None:
    assert parse_macos_idle(IOREG_SAMPLE) == 4.5


def test_macos_idle_without_the_field() -> None:
    assert parse_macos_idle("nothing here") is None
    assert parse_macos_idle("") is None


# --- macOS battery --------------------------------------------------------
def test_macos_battery_discharging() -> None:
    assert parse_macos_battery(PMSET_SAMPLE) == (87, False)


def test_macos_battery_on_ac() -> None:
    assert parse_macos_battery(PMSET_AC) == (100, True)


def test_macos_battery_bad_output() -> None:
    assert parse_macos_battery("no battery here") is None
    assert parse_macos_battery("") is None
    assert parse_macos_battery("weird %") is None


# --- Linux battery --------------------------------------------------------
def test_linux_battery_reads_the_first_battery(tmp_path) -> None:
    battery = tmp_path / "BAT0"
    battery.mkdir()
    (battery / "capacity").write_text("64", encoding="utf-8")
    (battery / "status").write_text("Discharging", encoding="utf-8")
    assert read_linux_battery(str(tmp_path)) == (64, False)


def test_linux_battery_charging(tmp_path) -> None:
    battery = tmp_path / "BAT0"
    battery.mkdir()
    (battery / "capacity").write_text("100", encoding="utf-8")
    (battery / "status").write_text("Full", encoding="utf-8")
    assert read_linux_battery(str(tmp_path)) == (100, True)


def test_linux_battery_skips_non_batteries(tmp_path) -> None:
    (tmp_path / "AC").mkdir()
    assert read_linux_battery(str(tmp_path)) is None


def test_linux_battery_missing_root(tmp_path) -> None:
    assert read_linux_battery(str(tmp_path / "nope")) is None


def test_linux_battery_bad_capacity(tmp_path) -> None:
    battery = tmp_path / "BAT0"
    battery.mkdir()
    (battery / "capacity").write_text("not a number", encoding="utf-8")
    assert read_linux_battery(str(tmp_path)) is None


# --- window geometry ------------------------------------------------------
def test_wmctrl_geometry_becomes_platforms() -> None:
    platforms = parse_wmctrl_geometry(WMCTRL_SAMPLE)
    assert (100, 900, 200) in platforms, "left, right, top of the editor window"
    assert (900, 1540, 50) in platforms


def test_wmctrl_geometry_skips_tiny_windows() -> None:
    assert all(right - left >= 80 for left, right, _top in parse_wmctrl_geometry(WMCTRL_SAMPLE))


def test_wmctrl_geometry_tolerates_junk() -> None:
    assert parse_wmctrl_geometry("") == []
    assert parse_wmctrl_geometry("garbage line") == []
    assert parse_wmctrl_geometry("0x1 0 x y 800 600 host Title") == []


# --- live probes ----------------------------------------------------------
def test_run_command_refuses_anything_not_allowlisted() -> None:
    assert run_command("rm -rf /") is None
    assert run_command("unknown_probe") is None
    assert run_command("") is None


def test_idle_seconds_shape() -> None:
    value = idle_seconds()
    assert value is None or value >= 0.0


def test_read_battery_shape() -> None:
    battery = read_battery()
    assert battery is None or (0 <= battery[0] <= 100 and isinstance(battery[1], bool))


def test_standable_windows_shape() -> None:
    for entry in standable_windows():
        assert len(entry) == 3
        left, right, _top = entry
        assert right >= left
