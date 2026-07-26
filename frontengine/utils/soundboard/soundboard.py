"""
音效板：一組「標籤 + 音檔 + 快速鍵」的格子，按下就播。

音檔路徑會先驗證存在且是檔案才收下——設定檔可能被手改壞，或音檔被搬走了。
播放用 QSoundEffect（短音效用它最合適，延遲低、可重疊）。

A soundboard: slots of label + sound file + hotkey, played on press.

A path is only accepted once it exists and is a file - settings can be
hand-edited and sounds get moved. Playback uses QSoundEffect, which is what
short effects want: low latency and overlappable.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, QUrl
from PySide6.QtMultimedia import QSoundEffect

from frontengine.utils.hotkey.hotkey_service import is_valid_hotkey
from frontengine.utils.logging.loggin_instance import front_engine_logger

MAX_SLOTS = 12
SOUND_SUFFIXES = (".wav", ".mp3", ".ogg", ".m4a", ".flac")


def normalize_slot(slot: Any) -> Optional[Dict[str, Any]]:
    """
    整理一格設定：要有存在的音檔，標籤沒填就用檔名。快速鍵格式不對就當作沒設。
    Normalize one slot: the sound must exist, and a blank label falls back to
    the file name. An invalid hotkey is treated as none rather than kept.
    """
    if not isinstance(slot, dict):
        return None
    path = str(slot.get("path", "")).strip()
    if not path:
        return None
    candidate = Path(path)
    if not candidate.is_file() or candidate.suffix.lower() not in SOUND_SUFFIXES:
        return None
    hotkey = str(slot.get("hotkey", "")).strip()
    if hotkey and not is_valid_hotkey(hotkey):
        hotkey = ""
    return {
        "label": str(slot.get("label", "")).strip() or candidate.stem,
        "path": str(candidate),
        "hotkey": hotkey,
        "volume": clamp_volume(slot.get("volume", 1.0)),
    }


def normalize_slots(slots: Any) -> List[Dict[str, Any]]:
    """整理整組設定，跳過壞掉或檔案不在的格子。"""
    if not isinstance(slots, (list, tuple)):
        return []
    cleaned = []
    for slot in slots:
        normalized = normalize_slot(slot)
        if normalized is not None:
            cleaned.append(normalized)
        if len(cleaned) >= MAX_SLOTS:
            break
    return cleaned


def clamp_volume(value: Any, fallback: float = 1.0) -> float:
    """音量夾在 0~1。"""
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return fallback


def hotkey_bindings(slots: Any) -> Dict[str, str]:
    """
    回傳 {動作名稱: 快速鍵}，動作名稱用 soundboard:<index> 以免和內建動作撞名。
    The {action: hotkey} map, namespaced as soundboard:<index> so it cannot
    collide with the built-in actions.
    """
    bindings: Dict[str, str] = {}
    for index, slot in enumerate(normalize_slots(slots)):
        if slot["hotkey"]:
            bindings[f"soundboard:{index}"] = slot["hotkey"]
    return bindings


def slot_index_for_action(action: Any) -> Optional[int]:
    """從動作名稱取出格子編號；不是音效板的動作回傳 None。"""
    text = str(action or "")
    if not text.startswith("soundboard:"):
        return None
    try:
        return int(text.split(":", 1)[1])
    except (TypeError, ValueError):
        return None


class Soundboard(QObject):
    """
    一組音效格。每一格的 QSoundEffect 會留著重複使用，按一次就重播一次。
    """

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.slots: List[Dict[str, Any]] = []
        self._effects: Dict[str, QSoundEffect] = {}

    def load(self, slots: Any) -> List[Dict[str, Any]]:
        """讀入一組設定（壞掉的格子會被跳過）。"""
        self.slots = normalize_slots(slots)
        self._effects = {key: effect for key, effect in self._effects.items()
                         if key in {slot["path"] for slot in self.slots}}
        return self.slots

    def add(self, path: str, label: str = "", hotkey: str = "") -> Optional[Dict[str, Any]]:
        """加一格；音檔不合格或已經滿了就回傳 None。"""
        if len(self.slots) >= MAX_SLOTS:
            front_engine_logger.info("[Soundboard] full, refusing another slot")
            return None
        slot = normalize_slot({"path": path, "label": label, "hotkey": hotkey})
        if slot is None:
            return None
        self.slots.append(slot)
        return slot

    def remove(self, index: int) -> bool:
        """刪掉一格。"""
        if 0 <= int(index) < len(self.slots):
            self.slots.pop(int(index))
            return True
        return False

    def _effect(self, slot: Dict[str, Any]) -> QSoundEffect:
        effect = self._effects.get(slot["path"])
        if effect is None:
            effect = QSoundEffect(self)
            effect.setSource(QUrl.fromLocalFile(slot["path"]))
            self._effects[slot["path"]] = effect
        effect.setVolume(clamp_volume(slot.get("volume", 1.0)))
        return effect

    def play(self, index: int) -> bool:
        """播第幾格；編號不存在回傳 False。"""
        position = int(index)
        if not (0 <= position < len(self.slots)):
            return False
        slot = self.slots[position]
        try:
            self._effect(slot).play()
        except Exception as error:  # pragma: no cover - audio backend boundary
            front_engine_logger.warning(f"[Soundboard] play failed: {error!r}")
            return False
        front_engine_logger.info(f"[Soundboard] play | {slot['label']}")
        return True

    def play_action(self, action: str) -> bool:
        """依快速鍵動作名稱播放。"""
        index = slot_index_for_action(action)
        return False if index is None else self.play(index)

    def to_list(self) -> List[Dict[str, Any]]:
        """轉成可儲存的資料。"""
        return [dict(slot) for slot in self.slots]

    def stop_all(self) -> None:
        """停掉所有還在播的音效。"""
        for effect in self._effects.values():
            try:
                effect.stop()
            except RuntimeError:  # pragma: no cover - already torn down
                pass
