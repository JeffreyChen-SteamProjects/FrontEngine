"""
省電模式：把覆蓋層的更新頻率整體調慢，換取較低的 CPU 與耗電。純計算，不依賴 Qt。

Low-power mode: slow every overlay's refresh rate down in exchange for lower
CPU use and battery drain. Pure maths, no Qt.
"""
from __future__ import annotations

# 省電時把間隔拉長的倍數，以及最慢不超過的上限（毫秒）
# How much longer each interval becomes, and the ceiling it never passes (ms).
LOW_POWER_FACTOR = 3
LOW_POWER_CEILING_MS = 250


def scaled_interval(base_ms, low_power: bool,
                    factor: int = LOW_POWER_FACTOR,
                    ceiling_ms: int = LOW_POWER_CEILING_MS) -> int:
    """
    回傳該用的更新間隔：一般模式用原值，省電模式放慢但不超過上限。
    The interval to use: the base one normally, a slower (capped) one in
    low-power mode.
    """
    try:
        base = max(1, int(base_ms))
    except (TypeError, ValueError):
        base = 33
    if not low_power:
        return base
    return min(max(base, int(ceiling_ms)), base * max(1, int(factor)))
