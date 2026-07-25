"""
讀取系統負載（CPU、記憶體、磁碟、網路流量）供覆蓋層顯示。Windows 走 ctypes
（GetSystemTimes / GlobalMemoryStatusEx / GetDiskFreeSpaceExW / GetIfTable），
Linux 走 /proc，其餘平台或失敗時對應欄位為 None，不新增任何相依套件。

Read system load (CPU, memory, disk, network throughput) for the overlays.
Windows uses ctypes (GetSystemTimes / GlobalMemoryStatusEx /
GetDiskFreeSpaceExW / GetIfTable), Linux reads /proc, and anything else leaves
the field as None. No extra dependencies.
"""
from __future__ import annotations

import sys
import time
from typing import Dict, Optional

from frontengine.utils.logging.loggin_instance import front_engine_logger

_ERROR_INSUFFICIENT_BUFFER = 122
_MAX_INTERFACE_NAME_LEN = 256
_MAXLEN_PHYSADDR = 8
_IF_TYPE_SOFTWARE_LOOPBACK = 24


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

    def __init__(self, disk_path: Optional[str] = None) -> None:
        self.disk_path = disk_path or ("C:\\" if sys.platform == "win32" else "/")
        self._previous_cpu = None          # (idle, total)
        self._previous_network = None      # (received, sent, timestamp)

    def sample(self) -> Dict[str, object]:
        """回傳 {cpu, ram, ram_used, ram_total, disk, disk_used, disk_total, down, up}。"""
        memory = self.memory()
        disk = self.disk()
        network = self.network()
        return {
            "cpu": self.cpu_percent(),
            "ram": percentage(memory[0], memory[1]) if memory else None,
            "ram_used": format_bytes(memory[0]) if memory else None,
            "ram_total": format_bytes(memory[1]) if memory else None,
            "disk": percentage(disk[0], disk[1]) if disk else None,
            "disk_used": format_bytes(disk[0]) if disk else None,
            "disk_total": format_bytes(disk[1]) if disk else None,
            "down": f"{format_bytes(network[0])}/s" if network and network[0] is not None else None,
            "up": f"{format_bytes(network[1])}/s" if network and network[1] is not None else None,
        }

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

            class _MIB_IFROW(ctypes.Structure):
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
            rows = ctypes.cast(
                ctypes.byref(buffer, ctypes.sizeof(ctypes.c_uint32)),
                ctypes.POINTER(_MIB_IFROW))
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
