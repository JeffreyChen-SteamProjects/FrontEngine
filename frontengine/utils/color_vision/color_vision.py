"""
色覺模擬：把畫面轉換成不同色盲類型看到的樣子，用來檢查自己做的東西在
別人眼裡分不分得出來。

轉換矩陣取自 Machado、Oliveira 與 Fernandes (2009) 的色覺缺陷模型，這也是
瀏覽器開發者工具與多數模擬器採用的那一套。純 numpy 計算，不碰畫面。

Colour-vision simulation: show what a design looks like to someone with a
colour vision deficiency, so "can they tell these apart?" has an answer.

The matrices come from Machado, Oliveira and Fernandes (2009) - the same model
browser devtools and most simulators use. Pure numpy; it never touches the
screen itself.
"""
from __future__ import annotations

from typing import Dict, Sequence, Tuple

import numpy

KIND_PROTANOPIA = "protanopia"
KIND_DEUTERANOPIA = "deuteranopia"
KIND_TRITANOPIA = "tritanopia"
KIND_ACHROMATOPSIA = "achromatopsia"
KINDS = (KIND_PROTANOPIA, KIND_DEUTERANOPIA, KIND_TRITANOPIA, KIND_ACHROMATOPSIA)

# 各類型的完全缺陷矩陣（severity = 1.0）
# The full-deficiency matrix for each kind (severity = 1.0).
_MATRICES: Dict[str, Tuple[Tuple[float, ...], ...]] = {
    KIND_PROTANOPIA: (
        (0.152286, 1.052583, -0.204868),
        (0.114503, 0.786281, 0.099216),
        (-0.003882, -0.048116, 1.051998),
    ),
    KIND_DEUTERANOPIA: (
        (0.367322, 0.860646, -0.227968),
        (0.280085, 0.672501, 0.047413),
        (-0.011820, 0.042940, 0.968881),
    ),
    KIND_TRITANOPIA: (
        (1.255528, -0.076749, -0.178779),
        (-0.078411, 0.930809, 0.147602),
        (0.004733, 0.691367, 0.303900),
    ),
    # 全色盲：用亮度權重把顏色壓成灰階
    # Achromatopsia: collapse to luminance.
    KIND_ACHROMATOPSIA: (
        (0.212656, 0.715158, 0.072186),
        (0.212656, 0.715158, 0.072186),
        (0.212656, 0.715158, 0.072186),
    ),
}
_IDENTITY = numpy.identity(3, dtype=numpy.float32)


def normalize_kind(kind) -> str:
    """把色覺類型正規化；不認得的一律當綠色盲（最常見的一種）。"""
    name = str(kind or "").strip().lower()
    return name if name in KINDS else KIND_DEUTERANOPIA


def clamp_severity(value) -> float:
    """嚴重程度夾在 0~1（0 等於沒有模擬）。"""
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 1.0


def matrix_for(kind, severity=1.0) -> numpy.ndarray:
    """
    某個類型在指定嚴重程度下的轉換矩陣：在單位矩陣與完全缺陷之間內插。
    The transform for a kind at a given severity, interpolated between identity
    and full deficiency.
    """
    full = numpy.array(_MATRICES[normalize_kind(kind)], dtype=numpy.float32)
    weight = clamp_severity(severity)
    return _IDENTITY * (1.0 - weight) + full * weight


def simulate_rgb(rgb: Sequence[int], kind, severity=1.0) -> Tuple[int, int, int]:
    """把單一顏色換成該色覺類型看到的顏色。"""
    values = list(rgb) if rgb is not None else []
    while len(values) < 3:
        values.append(0)
    source = numpy.array(values[:3], dtype=numpy.float32)
    result = matrix_for(kind, severity) @ source
    return tuple(int(round(max(0.0, min(255.0, channel)))) for channel in result)


def simulate_array(pixels: numpy.ndarray, kind, severity=1.0) -> numpy.ndarray:
    """
    把整張影像（H x W x 3，uint8）轉換成該色覺類型看到的樣子。
    Transform a whole image (H x W x 3, uint8) for the given kind.
    """
    data = numpy.asarray(pixels, dtype=numpy.float32)
    if data.ndim != 3 or data.shape[2] < 3:
        return numpy.asarray(pixels)
    matrix = matrix_for(kind, severity)
    converted = data[:, :, :3] @ matrix.T
    return numpy.clip(converted, 0, 255).astype(numpy.uint8)


def distinguishable(first: Sequence[int], second: Sequence[int], kind,
                    severity=1.0, threshold: int = 24) -> bool:
    """
    這兩個顏色在該色覺類型眼中還分得出來嗎？用轉換後的通道差距判斷。
    Can these two colours still be told apart with this deficiency? Judged on
    the channel distance after the transform.
    """
    left = simulate_rgb(first, kind, severity)
    right = simulate_rgb(second, kind, severity)
    return max(abs(a - b) for a, b in zip(left, right)) >= max(0, int(threshold))
