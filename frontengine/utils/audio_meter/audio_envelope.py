"""
把逐次取樣的音量峰值平滑成自然的脈動包絡：先在短窗內取 RMS 壓掉抖動，
再以「快起慢降」的包絡追蹤器塑形，避免忽大忽小的閃爍。純邏輯、不依賴 Qt。

Smooth per-tick peak samples into a natural pulse envelope: a short RMS window
removes jitter, then an asymmetric follower (fast attack, slow decay) shapes it.
Pure logic, no Qt dependency.
"""
from __future__ import annotations

from collections import deque


def clamp_level(value) -> float:
    """把任意輸入夾到 0~1；無法轉成數值時回傳 0.0。"""
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


class AudioEnvelope:
    """
    音量包絡追蹤器：push() 餵進一個 0~1 的峰值取樣，回傳平滑後的 0~1 音量。
    window 為 RMS 取樣窗長度，attack/decay 為上升/下降的追隨係數 (0~1，越大越快)。

    An envelope follower: push() takes one 0..1 peak sample and returns the
    smoothed 0..1 level. `window` is the RMS window length; `attack`/`decay`
    are the rise/fall follow coefficients (0..1, larger is faster).
    """

    def __init__(self, window: int = 4, attack: float = 0.6, decay: float = 0.12) -> None:
        self._window = max(1, int(window))
        self._samples: deque = deque(maxlen=self._window)
        self.attack = clamp_level(attack)
        self.decay = clamp_level(decay)
        self.value = 0.0

    def reset(self) -> None:
        """清空取樣與輸出（音源消失或關閉律動時呼叫）。"""
        self._samples.clear()
        self.value = 0.0

    def rms(self) -> float:
        """目前取樣窗的均方根；窗內無取樣時回傳 0.0。"""
        if not self._samples:
            return 0.0
        return (sum(sample * sample for sample in self._samples) / len(self._samples)) ** 0.5

    def push(self, level) -> float:
        """餵入一個峰值取樣並回傳平滑後的音量 / Feed one peak sample, return the smoothed level."""
        self._samples.append(clamp_level(level))
        target = self.rms()
        coefficient = self.attack if target > self.value else self.decay
        self.value = clamp_level(self.value + coefficient * (target - self.value))
        return self.value
