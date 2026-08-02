"""
讀取系統負載（CPU、記憶體、磁碟、網路流量、電池）供覆蓋層顯示。Windows 走 ctypes
（GetSystemTimes / GlobalMemoryStatusEx / GetDiskFreeSpaceExW / GetIfTable），
Linux 走 /proc，其餘平台或失敗時對應欄位為 None，不新增任何相依套件。
電池讀數借用 platform_info（三個平台都已實作），這裡只負責快取與併進取樣結果。

Read system load (CPU, memory, disk, network throughput, battery) for the
overlays. Windows uses ctypes (GetSystemTimes / GlobalMemoryStatusEx /
GetDiskFreeSpaceExW / GetIfTable), Linux reads /proc, and anything else leaves
the field as None. No extra dependencies. The battery reading comes from
platform_info, which already implements all three platforms; this module only
caches it and folds it into the sample.
"""
from __future__ import annotations

import sys
import time
from typing import Dict, Optional

from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.platform_info.platform_info import read_battery

_ERROR_INSUFFICIENT_BUFFER = 122
_MAX_INTERFACE_NAME_LEN = 256
_MAXLEN_PHYSADDR = 8
_IF_TYPE_SOFTWARE_LOOPBACK = 24
# 電池快取秒數。macOS 的讀數要開一個 pmset 子行程，而監控覆蓋層是每秒取樣的；
# 電量不會秒秒在變，快取讓每秒取樣不會每秒 fork 一次。
# Battery cache. Reading it on macOS spawns pmset, and the monitor overlay
# samples once a second; the charge does not move that fast, so the cache keeps
# a per-second sample from forking a process per second.
_BATTERY_CACHE_SECONDS = 30.0
STATE_CHARGING = "AC"
STATE_ON_BATTERY = "BAT"

# sample() 產生的欄位名稱。文字覆蓋層的樣板寫 `{cpu}`、`{down}` 就是查這些，
# 但畫面上原本沒有任何地方列出來，等於使用者得讀原始碼才知道能寫什麼。
# 這份清單是給 UI 顯示用的，和 sample() 的內容由測試釘在一起。
# The field names sample() produces. A text overlay template writes `{cpu}` or
# `{down}` to reach them, but nothing in the UI ever listed them - so knowing
# what could be written meant reading the source. This list is what the UI
# shows, and a test pins it to what sample() actually returns.
SAMPLE_FIELDS: tuple = (
    "cpu", "ram", "ram_used", "ram_total",
    "disk", "disk_used", "disk_total",
    "down", "up", "down_bytes", "up_bytes",
    "battery", "battery_state",
)


def percentage(part: float, whole: float) -> Optional[float]:
    """算出百分比並取到小數一位；分母為 0 或無效時回傳 None。"""
    try:
        if not whole:
            return None
        return round(max(0.0, min(100.0, 100.0 * float(part) / float(whole))), 1)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def format_bytes(size) -> str:
    """把位元組數格式化成易讀字串（B/KB/MB/GB/TB）。"""
    try:
        value = float(size)
    except (TypeError, ValueError):
        return "--"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(value) < 1024.0 or unit == "TB":
            return f"{value:.1f}{unit}" if unit != "B" else f"{int(value)}B"
        value /= 1024.0
    return f"{value:.1f}TB"


def rate_per_second(previous, current, elapsed: float, counter_bits: int = 32) -> Optional[float]:
    """
    以兩次計數器取樣算出每秒速率，並處理 32 位元計數器繞回。
    Rate per second between two counter samples, tolerating counter wrap-around.
    """
    if previous is None or current is None or elapsed <= 0:
        return None
    delta = current - previous
    if delta < 0:
        delta += 1 << counter_bits
    return max(0.0, delta / elapsed)


class SystemStats:
    """
    取樣系統負載。sample() 回傳可直接套進文字樣板的欄位；取不到的欄位為 None。
    Sample system load. sample() returns template-ready fields, None when a
    value cannot be read on this platform.
    """

    def __init__(self, disk_path: Optional[str] = None, battery_reader=None) -> None:
        self.disk_path = disk_path or ("C:\\" if sys.platform == "win32" else "/")
        self._previous_cpu = None          # (idle, total)
        self._previous_network = None      # (received, sent, timestamp)
        self._battery_reader = battery_reader or read_battery
        self._battery_cache = None         # (monotonic timestamp, reading)

    def sample(self) -> Dict[str, object]:
        """
        回傳可直接套進文字樣板的欄位。速率同時給格式化字串（`down` / `up`，
        給文字覆蓋層看）與原始 bytes/s（`down_bytes` / `up_bytes`，給折線圖用），
        因為折線需要的是數字，而樣板需要的是「1.2MB/s」。
        Template-ready fields. Throughput appears twice: formatted (`down` /
        `up`) for text overlays and raw bytes per second (`down_bytes` /
        `up_bytes`) for the sparklines, because a graph needs a number where a
        template needs "1.2MB/s".
        """
        memory = self.memory()
        disk = self.disk()
        network = self.network()
        battery = self.battery()
        down_bytes = network[0] if network else None
        up_bytes = network[1] if network else None
        return {
            "cpu": self.cpu_percent(),
            "ram": percentage(memory[0], memory[1]) if memory else None,
            "ram_used": format_bytes(memory[0]) if memory else None,
            "ram_total": format_bytes(memory[1]) if memory else None,
            "disk": percentage(disk[0], disk[1]) if disk else None,
            "disk_used": format_bytes(disk[0]) if disk else None,
            "disk_total": format_bytes(disk[1]) if disk else None,
            "down": f"{format_bytes(down_bytes)}/s" if down_bytes is not None else None,
            "up": f"{format_bytes(up_bytes)}/s" if up_bytes is not None else None,
            "down_bytes": float(down_bytes) if down_bytes is not None else None,
            "up_bytes": float(up_bytes) if up_bytes is not None else None,
            "battery": float(battery[0]) if battery else None,
            "battery_state": (STATE_CHARGING if battery[1] else STATE_ON_BATTERY)
            if battery else None,
        }

    # --- battery ---------------------------------------------------------
    def battery(self):
        """
        (電量百分比, 是否充電中)；沒有電池或讀不到回傳 None。讀數快取
        `_BATTERY_CACHE_SECONDS` 秒，理由見該常數。
        (charge percent, charging) or None when there is no battery or it
        cannot be read. Cached — see `_BATTERY_CACHE_SECONDS`.
        """
        now = time.monotonic()
        cached = self._battery_cache
        if cached is not None and now - cached[0] < _BATTERY_CACHE_SECONDS:
            return cached[1]
        try:
            reading = self._battery_reader()
        except Exception as error:  # pragma: no cover - defensive around the platform call
            front_engine_logger.warning(f"[SystemStats] battery read failed: {error!r}")
            reading = None
        self._battery_cache = (now, reading)
        return reading

    # --- CPU -------------------------------------------------------------
    def cpu_percent(self) -> Optional[float]:
        """兩次取樣之間的 CPU 使用率；第一次取樣沒有可比對的基準，回傳 None。"""
        times = self._cpu_times()
        if times is None:
            return None
        idle, total = times
        previous = self._previous_cpu
        self._previous_cpu = times
        if previous is None:
            return None
        idle_delta = idle - previous[0]
        total_delta = total - previous[1]
        if total_delta <= 0:
            return None
        return percentage(total_delta - idle_delta, total_delta)

    def _cpu_times(self):
        if sys.platform == "win32":
            return self._cpu_times_windows()
        return self._cpu_times_proc()

    @staticmethod
    def _cpu_times_windows():
        try:
            import ctypes
            from ctypes.wintypes import FILETIME

            idle, kernel, user = FILETIME(), FILETIME(), FILETIME()
            if not ctypes.windll.kernel32.GetSystemTimes(
                    ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)):
                return None

            def to_int(value: FILETIME) -> int:
                return (value.dwHighDateTime << 32) | value.dwLowDateTime

            idle_time = to_int(idle)
            total = to_int(kernel) + to_int(user)
            return (idle_time, total)
        except Exception as error:  # pragma: no cover - Win32 boundary
            front_engine_logger.debug(f"[SystemStats] GetSystemTimes failed: {error!r}")
            return None

    @staticmethod
    def _cpu_times_proc():
        try:
            with open("/proc/stat", "r", encoding="utf-8") as handle:
                fields = handle.readline().split()
            values = [float(field) for field in fields[1:]]
            return (values[3], sum(values))
        except (OSError, IndexError, ValueError):
            return None

    # --- memory ----------------------------------------------------------
    def memory(self):
        """回傳 (已用位元組, 總位元組)；取不到回傳 None。"""
        if sys.platform == "win32":
            return self._memory_windows()
        return self._memory_proc()

    @staticmethod
    def _memory_windows():
        try:
            import ctypes

            class _MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_uint32),
                    ("dwMemoryLoad", ctypes.c_uint32),
                    ("ullTotalPhys", ctypes.c_uint64),
                    ("ullAvailPhys", ctypes.c_uint64),
                    ("ullTotalPageFile", ctypes.c_uint64),
                    ("ullAvailPageFile", ctypes.c_uint64),
                    ("ullTotalVirtual", ctypes.c_uint64),
                    ("ullAvailVirtual", ctypes.c_uint64),
                    ("ullAvailExtendedVirtual", ctypes.c_uint64),
                ]

            status = _MEMORYSTATUSEX()
            status.dwLength = ctypes.sizeof(status)
            if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return None
            return (status.ullTotalPhys - status.ullAvailPhys, status.ullTotalPhys)
        except Exception as error:  # pragma: no cover - Win32 boundary
            front_engine_logger.debug(f"[SystemStats] GlobalMemoryStatusEx failed: {error!r}")
            return None

    @staticmethod
    def _memory_proc():
        try:
            values = {}
            with open("/proc/meminfo", "r", encoding="utf-8") as handle:
                for line in handle:
                    key, _, rest = line.partition(":")
                    values[key.strip()] = float(rest.split()[0]) * 1024
            total = values.get("MemTotal")
            available = values.get("MemAvailable", values.get("MemFree"))
            if total is None or available is None:
                return None
            return (total - available, total)
        except (OSError, IndexError, ValueError):
            return None

    # --- disk ------------------------------------------------------------
    def disk(self):
        """回傳目標磁碟的 (已用位元組, 總位元組)；取不到回傳 None。"""
        try:
            import shutil

            usage = shutil.disk_usage(self.disk_path)
            return (usage.used, usage.total)
        except (OSError, ValueError) as error:
            front_engine_logger.debug(f"[SystemStats] disk_usage failed: {error!r}")
            return None

    # --- network ---------------------------------------------------------
    def network(self):
        """回傳 (下載 B/s, 上傳 B/s)；第一次取樣或無法取得時為 (None, None)。"""
        counters = self._network_counters()
        if counters is None:
            return None
        now = time.monotonic()
        previous = self._previous_network
        self._previous_network = (counters[0], counters[1], now)
        if previous is None:
            return (None, None)
        elapsed = now - previous[2]
        return (
            rate_per_second(previous[0], counters[0], elapsed, counter_bits=64),
            rate_per_second(previous[1], counters[1], elapsed, counter_bits=64),
        )

    def _network_counters(self):
        if sys.platform == "win32":
            return self._network_counters_windows()
        return self._network_counters_proc()

    @staticmethod
    def _network_counters_windows():
        """加總所有非回送介面的收送位元組（GetIfTable）。"""
        try:
            import ctypes

            class _MibIfRow(ctypes.Structure):
                _fields_ = [
                    ("wszName", ctypes.c_wchar * _MAX_INTERFACE_NAME_LEN),
                    ("dwIndex", ctypes.c_uint32),
                    ("dwType", ctypes.c_uint32),
                    ("dwMtu", ctypes.c_uint32),
                    ("dwSpeed", ctypes.c_uint32),
                    ("dwPhysAddrLen", ctypes.c_uint32),
                    ("bPhysAddr", ctypes.c_ubyte * _MAXLEN_PHYSADDR),
                    ("dwAdminStatus", ctypes.c_uint32),
                    ("dwOperStatus", ctypes.c_uint32),
                    ("dwLastChange", ctypes.c_uint32),
                    ("dwInOctets", ctypes.c_uint32),
                    ("dwInUcastPkts", ctypes.c_uint32),
                    ("dwInNUcastPkts", ctypes.c_uint32),
                    ("dwInDiscards", ctypes.c_uint32),
                    ("dwInErrors", ctypes.c_uint32),
                    ("dwInUnknownProtos", ctypes.c_uint32),
                    ("dwOutOctets", ctypes.c_uint32),
                    ("dwOutUcastPkts", ctypes.c_uint32),
                    ("dwOutNUcastPkts", ctypes.c_uint32),
                    ("dwOutDiscards", ctypes.c_uint32),
                    ("dwOutErrors", ctypes.c_uint32),
                    ("dwOutQLen", ctypes.c_uint32),
                    ("dwDescrLen", ctypes.c_uint32),
                    ("bDescr", ctypes.c_ubyte * 256),
                ]

            iphlpapi = ctypes.windll.iphlpapi
            size = ctypes.c_uint32(0)
            if iphlpapi.GetIfTable(None, ctypes.byref(size), False) != _ERROR_INSUFFICIENT_BUFFER:
                return None
            buffer = ctypes.create_string_buffer(size.value)
            if iphlpapi.GetIfTable(buffer, ctypes.byref(size), False) != 0:
                return None
            count = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_uint32))[0]
            # 從緩衝區位址往後跳過開頭的計數欄位，再當成 row 陣列讀。
            # 用 addressof + 位移比把 byref 的結果丟給 cast 明確得多。
            # Step past the leading count field by address and read the rest as
            # rows. addressof plus an offset is far clearer than handing cast
            # the result of byref.
            rows = ctypes.cast(
                ctypes.addressof(buffer)  # NOSONAR - a char array is a ctypes instance
                + ctypes.sizeof(ctypes.c_uint32),
                ctypes.POINTER(_MibIfRow))
            received = sent = 0
            for index in range(count):
                row = rows[index]
                if row.dwType == _IF_TYPE_SOFTWARE_LOOPBACK:
                    continue
                received += row.dwInOctets
                sent += row.dwOutOctets
            return (received, sent)
        except Exception as error:  # pragma: no cover - Win32 boundary
            front_engine_logger.debug(f"[SystemStats] GetIfTable failed: {error!r}")
            return None

    @staticmethod
    def _network_counters_proc():
        try:
            received = sent = 0
            with open("/proc/net/dev", "r", encoding="utf-8") as handle:
                for line in handle.readlines()[2:]:
                    name, _, rest = line.partition(":")
                    if name.strip() == "lo":
                        continue
                    fields = rest.split()
                    received += int(fields[0])
                    sent += int(fields[8])
            return (received, sent)
        except (OSError, IndexError, ValueError):
            return None


_stats_singleton: Optional[SystemStats] = None


def system_stats() -> Dict[str, object]:
    """便利函式：以共用取樣器回傳目前的系統負載欄位。"""
    global _stats_singleton
    if _stats_singleton is None:
        _stats_singleton = SystemStats()
    return _stats_singleton.sample()
