"""
把「螢幕」對應到「輸出音源端點」：多螢幕時，各螢幕常各自帶喇叭（HDMI/DP 音訊），
本模組以端點顯示名稱與螢幕型號/製造商的共同字詞比對，讓每隻寵物跟著自己所在
螢幕的聲音律動；比不到對應端點時退回預設輸出裝置。

Map a screen to an audio output endpoint. On multi-monitor setups each screen
often carries its own speakers (HDMI/DP audio); this matches endpoint friendly
names against the screen's model/manufacturer so a pet pulses to the sound of
the screen it lives on, falling back to the default endpoint when unmatched.
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Tuple

from frontengine.utils.audio_meter.system_audio_meter import (
    SystemAudioMeter, list_output_devices, system_audio_level,
)
from frontengine.utils.logging.loggin_instance import front_engine_logger

# 比對時要忽略的通用字詞（裝置與螢幕名稱都常出現，沒有辨識力）
# Generic words that carry no identifying power when matching names.
_GENERIC_TOKENS = frozenset({
    "audio", "sound", "speaker", "speakers", "headphone", "headphones", "headset",
    "digital", "output", "high", "definition", "device", "generic", "pnp", "plug",
    "play", "monitor", "display", "screen", "hdmi", "displayport", "the", "and",
    "nvidia", "intel", "amd", "realtek", "usb", "default", "communications",
})


def name_tokens(text) -> set:
    """把名稱切成可比對的小寫字詞，去掉通用字詞與過短片段。"""
    if not text:
        return set()
    tokens = set()
    word = []
    for character in str(text).lower():
        if character.isalnum():
            word.append(character)
            continue
        if word:
            tokens.add("".join(word))
            word = []
    if word:
        tokens.add("".join(word))
    return {token for token in tokens if len(token) >= 2 and token not in _GENERIC_TOKENS}


def match_device_for_screen(hints: Iterable[str], devices: Iterable[Tuple[str, str]]) -> Optional[str]:
    """
    以共同字詞數挑出最像該螢幕的輸出端點，回傳 device_id；沒有共同字詞回傳 None。
    Pick the endpoint sharing the most tokens with the screen hints, or None.
    """
    hint_tokens = set()
    for hint in hints or ():
        hint_tokens |= name_tokens(hint)
    if not hint_tokens:
        return None
    best_id = None
    best_score = 0
    for device_id, name in devices or ():
        score = len(hint_tokens & name_tokens(name))
        if score > best_score:
            best_score = score
            best_id = device_id
    return best_id


def screen_hints(screen) -> List[str]:
    """從 QScreen 取出可比對的字串（型號、製造商、名稱），取不到就略過。"""
    hints: List[str] = []
    for attribute in ("model", "manufacturer", "name"):
        getter = getattr(screen, attribute, None)
        if not callable(getter):
            continue
        try:
            value = getter()
        except Exception:  # pragma: no cover - defensive against Qt/duck-typed screens
            continue
        if value:
            hints.append(str(value))
    return hints


class ScreenAudioMeters:
    """依裝置 ID 快取電表，並提供「綁定某螢幕音源」的取樣函式。"""

    def __init__(self) -> None:
        self._meters: Dict[str, SystemAudioMeter] = {}

    def device_for_screen(self, screen) -> Optional[str]:
        """回傳該螢幕對應的輸出端點 ID；沒有對應者回傳 None。"""
        if screen is None:
            return None
        return match_device_for_screen(screen_hints(screen), list_output_devices())

    def level_for_device(self, device_id: str) -> Optional[float]:
        """讀取指定端點的目前峰值（電表物件會重複使用）。"""
        meter = self._meters.get(device_id)
        if meter is None:
            meter = SystemAudioMeter(device_id)
            self._meters[device_id] = meter
        return meter.level()

    def provider_for_screen(self, screen):
        """
        回傳取樣函式：優先跟隨該螢幕的音源，比對不到則沿用系統預設輸出裝置。
        Return a level provider bound to the screen's endpoint, or the default one.
        """
        device_id = self.device_for_screen(screen)
        if device_id is None:
            return system_audio_level
        front_engine_logger.info(f"[ScreenAudioMeters] screen audio endpoint | id={device_id}")
        return lambda: self.level_for_device(device_id)

    def close(self) -> None:
        """釋放所有已建立的電表 / Release every meter created so far."""
        for meter in self._meters.values():
            meter.close()
        self._meters.clear()


_screen_meters = ScreenAudioMeters()


def audio_level_provider_for_screen(screen):
    """便利函式：取得跟隨指定螢幕音源的取樣函式（共用電表快取）。"""
    return _screen_meters.provider_for_screen(screen)
