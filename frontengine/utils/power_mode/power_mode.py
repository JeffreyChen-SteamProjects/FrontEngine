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


# --- 畫質檔位 / quality tiers ----------------------------------------------
# 比「省電開／關」更細的三段：更新頻率上限與算圖縮放各自不同。
# Three steps instead of one on/off switch: each caps the refresh rate and
# scales the render resolution differently.
TIER_HIGH = "high"
TIER_BALANCED = "balanced"
TIER_SAVER = "saver"

# 檔位 -> (最快多久更新一次 ms, 算圖縮放)
# tier -> (fastest allowed interval in ms, render scale)
QUALITY_TIERS = {
    TIER_HIGH: (0, 1.0),
    TIER_BALANCED: (33, 0.85),   # 約 30 FPS / roughly 30 FPS
    TIER_SAVER: (100, 0.6),      # 約 10 FPS / roughly 10 FPS
}
DEFAULT_TIER = TIER_HIGH


def normalize_tier(tier) -> str:
    """把畫質檔位正規化；不認得的值一律當成最高畫質。"""
    name = str(tier or "").strip().lower()
    return name if name in QUALITY_TIERS else DEFAULT_TIER


def tier_interval(base_ms, tier) -> int:
    """
    套用畫質檔位後該用的更新間隔：不快過該檔位的上限。
    The interval to use at this tier: never faster than the tier's floor.
    """
    try:
        base = max(1, int(base_ms))
    except (TypeError, ValueError):
        base = 33
    floor_ms, _scale = QUALITY_TIERS[normalize_tier(tier)]
    return max(base, int(floor_ms))


def tier_render_scale(tier) -> float:
    """該檔位的算圖縮放（1.0 = 原生解析度）。"""
    _floor_ms, scale = QUALITY_TIERS[normalize_tier(tier)]
    return float(scale)
