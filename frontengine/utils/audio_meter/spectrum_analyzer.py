"""
把一段音訊樣本換成畫得出來的頻譜條：做 FFT、依對數間隔分成幾個頻段、
再各自平滑並保留一個會慢慢落下的峰值。純計算（只用 numpy），不碰音訊裝置，
所以在任何平台都能測。

Turn a chunk of audio samples into bars you can draw: FFT it, group the bins
into log-spaced bands, then smooth each band and keep a peak that falls back
slowly. Pure maths on numpy - it never touches an audio device, so it is
testable anywhere.
"""
from __future__ import annotations

from typing import List, Optional, Sequence

import numpy

DEFAULT_BANDS = 24
MIN_BANDS = 2
MAX_BANDS = 96
# 人耳大致聽得到的範圍；低於 20Hz 幾乎只有直流與雜訊
# Roughly the audible range; below 20 Hz is mostly DC and noise.
MIN_FREQUENCY = 30.0
MAX_FREQUENCY = 16000.0
# 把 dB 對應到 0~1 時的下限（比這更安靜就當作 0）
# The floor used when mapping dB to 0..1; quieter than this counts as silence.
FLOOR_DB = -70.0


def clamp_bands(value, fallback: int = DEFAULT_BANDS) -> int:
    """頻段數量夾在能畫得出來的範圍。"""
    try:
        return max(MIN_BANDS, min(MAX_BANDS, int(value)))
    except (TypeError, ValueError):
        return fallback


def band_edges(bands: int = DEFAULT_BANDS, sample_rate: int = 48000,
               fft_size: int = 1024) -> List[int]:
    """
    每個頻段對應到的 FFT bin 邊界（對數間隔，低頻窄、高頻寬，看起來才自然）。
    The FFT bin boundaries for each band - log spaced, so the low end gets the
    detail the ear expects.
    """
    count = clamp_bands(bands)
    bin_count = max(2, int(fft_size) // 2)
    resolution = float(sample_rate) / max(1, int(fft_size))
    highest = min(MAX_FREQUENCY, float(sample_rate) / 2.0)
    frequencies = numpy.geomspace(MIN_FREQUENCY, max(MIN_FREQUENCY * 2, highest), count + 1)
    edges = [int(min(bin_count, max(1, round(frequency / resolution)))) for frequency in frequencies]
    # 保證每個頻段至少涵蓋一個 bin，否則低頻幾段會全部擠在一起
    # Guarantee each band owns at least one bin, or the low bands collapse together.
    for index in range(1, len(edges)):
        edges[index] = max(edges[index], edges[index - 1] + 1)
    return [min(edge, bin_count) for edge in edges]


def to_mono(samples: Sequence[float], channels: int = 1) -> numpy.ndarray:
    """把交錯的多聲道樣本平均成單聲道。"""
    data = numpy.asarray(samples, dtype=numpy.float32).ravel()
    channel_count = max(1, int(channels))
    if channel_count == 1 or data.size < channel_count:
        return data
    usable = data.size - (data.size % channel_count)
    return data[:usable].reshape(-1, channel_count).mean(axis=1)


def magnitudes_to_levels(magnitudes: numpy.ndarray) -> numpy.ndarray:
    """把 FFT 強度換成 0~1：先轉 dB，再以 FLOOR_DB 為底線正規化。"""
    safe = numpy.maximum(magnitudes, 1e-10)
    decibels = 20.0 * numpy.log10(safe)
    return numpy.clip((decibels - FLOOR_DB) / (-FLOOR_DB), 0.0, 1.0)


def spectrum_bands(samples: Sequence[float], sample_rate: int = 48000,
                   bands: int = DEFAULT_BANDS, channels: int = 1) -> List[float]:
    """
    一段樣本 -> 每個頻段的強度 (0~1)。樣本不足時回傳全 0，呼叫端不必特別處理。
    A chunk of samples to a level per band (0..1). Too few samples gives zeros,
    so callers never have to special-case a short read.
    """
    count = clamp_bands(bands)
    mono = to_mono(samples, channels)
    if mono.size < 32:
        return [0.0] * count
    fft_size = 1 << int(numpy.floor(numpy.log2(mono.size)))
    window = numpy.hanning(fft_size)
    spectrum = numpy.abs(numpy.fft.rfft(mono[:fft_size] * window)) / (fft_size / 2)
    levels = magnitudes_to_levels(spectrum[1:])  # bin 0 是直流，不要它
    edges = band_edges(count, sample_rate, fft_size)
    result: List[float] = []
    for index in range(count):
        low, high = edges[index] - 1, edges[index + 1] - 1
        chunk = levels[max(0, low):max(low + 1, high)]
        result.append(float(chunk.max()) if chunk.size else 0.0)
    return result


class SpectrumSmoother:
    """
    讓頻譜條看起來像在呼吸而不是在抖：上升快、下降慢，另外記一個會慢慢
    落下的峰值標記。attack/decay 是每次更新保留多少舊值。
    Keep the bars breathing instead of flickering: rise fast, fall slowly, and
    carry a peak marker that drifts down. attack/decay are how much of the old
    value survives each update.
    """

    def __init__(self, bands: int = DEFAULT_BANDS, attack: float = 0.25,
                 decay: float = 0.82, peak_decay: float = 0.02) -> None:
        self.bands = clamp_bands(bands)
        self.attack = float(attack)
        self.decay = float(decay)
        self.peak_decay = float(peak_decay)
        self.levels: List[float] = [0.0] * self.bands
        self.peaks: List[float] = [0.0] * self.bands

    def reset(self) -> None:
        self.levels = [0.0] * self.bands
        self.peaks = [0.0] * self.bands

    def set_bands(self, bands: int) -> None:
        """改變頻段數量並重新開始。"""
        self.bands = clamp_bands(bands)
        self.reset()

    def push(self, values: Optional[Sequence[float]]) -> List[float]:
        """
        餵一組新的頻段強度，回傳平滑後的值。傳 None 代表沒有訊號，讓所有
        條慢慢落回去而不是瞬間歸零。
        """
        incoming = list(values or [])
        for index in range(self.bands):
            target = 0.0
            if index < len(incoming):
                try:
                    target = max(0.0, min(1.0, float(incoming[index])))
                except (TypeError, ValueError):
                    target = 0.0
            current = self.levels[index]
            weight = self.attack if target > current else self.decay
            current = current * weight + target * (1.0 - weight)
            self.levels[index] = current
            self.peaks[index] = max(current, self.peaks[index] - self.peak_decay)
        return list(self.levels)
