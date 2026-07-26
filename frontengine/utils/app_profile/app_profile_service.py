"""
依前景程式自動套用預設集：例如切到剪輯軟體就換成「工作」那組覆蓋層設定，
切回瀏覽器就換回「休閒」那組。只在前景程式「換人」時觸發一次，避免每次
輪詢都重套一遍。

Per-app profiles: apply a preset when a given app takes focus - the "work" set
of overlays for the editor, the "play" set for the browser. It fires once when
the foreground app changes, never on every poll.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from PySide6.QtCore import QObject, QTimer, Signal

from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.platform_info.platform_info import active_app_name
from frontengine.utils.smart_pause.pause_rules import normalize_app_name


def normalize_profiles(config: Any) -> Dict[str, str]:
    """
    把設定裡的 {程式: 預設集} 對照表正規化：程式名稱轉小寫去副檔名，
    空白項目丟掉。格式不對就回傳空 dict。
    Normalize the {app: preset} map from settings - app names lowercased and
    stripped of .exe, blank entries dropped. Anything malformed gives {}.
    """
    if not isinstance(config, dict):
        return {}
    profiles: Dict[str, str] = {}
    for app, preset in config.items():
        name = normalize_app_name(app)
        preset_name = str(preset).strip() if preset is not None else ""
        if name and preset_name:
            profiles[name] = preset_name
    return profiles


def preset_for_app(app: Any, config: Any) -> Optional[str]:
    """該程式對應的預設集名稱；沒有對應就回傳 None。"""
    name = normalize_app_name(app)
    if not name:
        return None
    return normalize_profiles(config).get(name)


class AppProfileService(QObject):
    """
    輪詢前景程式，換到有設定的程式時發出要套用的預設集名稱。程式來源與
    設定來源都可注入，測試不需要真的切視窗。
    Poll the foreground app and emit the preset to apply when focus moves to an
    app that has one configured. Both the app probe and the config are
    injectable, so tests never need a real window switch.
    """

    profile_due = Signal(str)

    def __init__(
        self,
        config_provider: Optional[Callable[[], Dict[str, Any]]] = None,
        app_provider: Optional[Callable[[], Optional[str]]] = None,
        interval_ms: int = 2000,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._config_provider: Callable[[], Dict[str, Any]] = config_provider or (lambda: {})
        self._app_provider: Callable[[], Optional[str]] = app_provider or active_app_name
        self._current_app: str = ""
        self._timer = QTimer(self)
        self._timer.setInterval(max(250, int(interval_ms)))
        self._timer.timeout.connect(self.poll_once)

    @property
    def current_app(self) -> str:
        return self._current_app

    def start(self) -> None:
        front_engine_logger.info("[AppProfile] start")
        self._timer.start()

    def stop(self) -> None:
        front_engine_logger.info("[AppProfile] stop")
        self._timer.stop()

    def poll_once(self) -> None:
        """檢查一次前景程式（測試會直接呼叫）。"""
        try:
            config = self._config_provider() or {}
            profiles = normalize_profiles(config)
            if not profiles:
                return
            name = normalize_app_name(self._app_provider())
        except Exception as error:  # pragma: no cover - defensive boundary
            front_engine_logger.warning(f"[AppProfile] poll error: {error!r}")
            return
        if not name or name == self._current_app:
            return
        self._current_app = name
        preset = profiles.get(name)
        if preset:
            front_engine_logger.info(f"[AppProfile] {name} -> {preset}")
            self.profile_due.emit(preset)
