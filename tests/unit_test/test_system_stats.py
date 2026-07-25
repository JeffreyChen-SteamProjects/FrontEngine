"""
系統負載讀取的測試：純計算部分嚴格驗證，實機取樣只檢查型別與範圍
（CI 上不同機器數值不同，也可能取不到）。

Tests for system load sampling: the pure maths is asserted exactly, while live
sampling is only checked for shape and range — values differ per machine and
may be unavailable entirely.
"""
from frontengine.utils.system_stats.system_stats import (
    SystemStats, format_bytes, percentage, rate_per_second, system_stats,
)

NUMERIC_FIELDS = ("cpu", "ram", "disk")
TEXT_FIELDS = ("ram_used", "ram_total", "disk_used", "disk_total", "down", "up")


def test_percentage_rounds_and_clamps() -> None:
    assert percentage(1, 4) == 25.0
    assert percentage(1, 3) == 33.3
    assert percentage(5, 4) == 100.0, "clamped at 100"
    assert percentage(-1, 4) == 0.0, "clamped at 0"


def test_percentage_rejects_bad_input() -> None:
    assert percentage(1, 0) is None
    assert percentage(1, None) is None
    assert percentage("x", 4) is None


def test_format_bytes_scales() -> None:
    assert format_bytes(0) == "0B"
    assert format_bytes(512) == "512B"
    assert format_bytes(1536) == "1.5KB"
    assert format_bytes(5 * 1024 ** 3) == "5.0GB"
    assert format_bytes(3 * 1024 ** 4) == "3.0TB"
    assert format_bytes("junk") == "--"


def test_rate_per_second_basics() -> None:
    assert rate_per_second(0, 100, 2.0) == 50.0
    assert rate_per_second(None, 100, 2.0) is None
    assert rate_per_second(0, 100, 0) is None


def test_rate_per_second_handles_counter_wrap() -> None:
    wrapped = rate_per_second(2 ** 32 - 10, 90, 1.0)
    assert wrapped == 100.0, "a 32-bit counter that wrapped is not a negative rate"
    assert rate_per_second(2 ** 64 - 10, 90, 1.0, counter_bits=64) == 100.0


def test_sample_has_every_field() -> None:
    sample = SystemStats().sample()
    assert set(sample) == set(NUMERIC_FIELDS) | set(TEXT_FIELDS)


def test_numeric_fields_are_percentages_or_unavailable() -> None:
    sample = SystemStats().sample()
    for field in NUMERIC_FIELDS:
        value = sample[field]
        assert value is None or 0.0 <= value <= 100.0, field


def test_text_fields_are_strings_or_unavailable() -> None:
    sample = SystemStats().sample()
    for field in TEXT_FIELDS:
        value = sample[field]
        assert value is None or isinstance(value, str), field


def test_cpu_and_network_need_two_samples() -> None:
    stats = SystemStats()
    assert stats.cpu_percent() is None, "the first sample has nothing to compare against"
    second = stats.cpu_percent()
    assert second is None or 0.0 <= second <= 100.0


def test_repeated_sampling_is_stable() -> None:
    stats = SystemStats()
    for _ in range(3):
        stats.sample()  # must not raise on any platform


def test_a_missing_disk_path_degrades() -> None:
    stats = SystemStats(disk_path="Z:\\no-such-drive-here")
    assert stats.disk() is None
    sample = stats.sample()
    assert sample["disk"] is None and sample["disk_total"] is None


def test_module_helper_returns_a_sample() -> None:
    assert set(system_stats()) == set(NUMERIC_FIELDS) | set(TEXT_FIELDS)
