"""
保持喚醒：開著覆蓋層的時候別讓螢幕睡著。

這是螢幕保護的另一面。放了影片、看板或簡報層在畫面上，系統照樣會在幾分鐘後把
螢幕關掉——那正是最不該關的時候。

三個平台各自用系統既有的方式，都不需要新相依：Windows 是一個 Win32 呼叫，
macOS 與 Linux 是常駐一個系統本來就有的小程式（`caffeinate` / `systemd-inhibit`）
並在結束時終止它。做不到的平台照實回報，不假裝成功。

Keep awake: stop the screen sleeping while an overlay is up.

This is the other side of the screensaver. With a video, a signage rotation or a
presenting layer on screen, the system still blanks the display after a few
minutes - exactly when it should not.

Each platform uses what it already has, with no new dependency: one Win32 call on
Windows, and on macOS and Linux a small program that ships with the system
(`caffeinate` / `systemd-inhibit`) held open and terminated on release. A
platform that cannot do it says so rather than pretending.
"""
from __future__ import annotations

import shutil
import subprocess  # nosec B404 - only runs the fixed argv in _HELPERS below
import sys
from typing import List, Optional

from frontengine.utils.logging.loggin_instance import front_engine_logger

# SetThreadExecutionState 的旗標 / Flags for SetThreadExecutionState
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002

# 非 Windows 平台用的常駐小程式。argv 全部寫死在這裡，沒有任何外部輸入。
# The helper held open on the other platforms. Every argv is literal here; no
# outside input reaches it.
_HELPERS = {
    "darwin": ["/usr/bin/caffeinate", "-dimsu"],
    "linux": ["systemd-inhibit", "--what=idle:sleep",
              "--who=FrontEngine", "--why=Overlay on screen", "--mode=block",
              "sleep", "infinity"],
}


def helper_command() -> Optional[List[str]]:
    """這個平台要跑哪一個小程式；Windows 或找不到程式時回傳 None。"""
    command = _HELPERS.get(sys.platform)
    if command is None:
        return None
    return command if shutil.which(command[0]) else None


def available() -> bool:
    """這個平台能不能阻止螢幕睡著。"""
    if sys.platform == "win32":
        return True
    return helper_command() is not None


class KeepAwake:
    """
    保持喚醒的開關。enable() 開始、disable() 放開，兩者重複呼叫都是安全的。

    **一定要記得放開。** Windows 的執行緒執行狀態會跟著行程活著，忘了還原的話，
    使用者關掉這個選項、甚至關掉整個程式之後，螢幕還是不會依設定睡著——而且看不出
    是誰造成的。
    A keep-awake switch. enable() holds it, disable() lets go, and both are safe
    to call twice.

    **Releasing matters.** The Windows execution state lives as long as the
    process: forget to restore it and the display stops sleeping even after the
    user switches the option off, with nothing on screen to say why.
    """

    def __init__(self) -> None:
        self._active = False
        self._process: Optional[subprocess.Popen] = None

    @property
    def active(self) -> bool:
        return self._active

    def enable(self, keep_display_on: bool = True) -> bool:
        """開始保持喚醒；做不到就回傳 False。"""
        if self._active:
            return True
        if not available():
            front_engine_logger.info("[KeepAwake] not supported on this platform")
            return False
        if sys.platform == "win32":
            if not self._windows_state(keep_display_on):
                return False
        elif not self._start_helper():
            return False
        self._active = True
        front_engine_logger.info(f"[KeepAwake] on | display={keep_display_on}")
        return True

    def disable(self) -> None:
        """放開，讓系統回到原本的睡眠設定。重複呼叫是安全的。"""
        if not self._active:
            return
        if sys.platform == "win32":
            self._windows_state(False, release=True)
        self._stop_helper()
        self._active = False
        front_engine_logger.info("[KeepAwake] off")

    # --- platform boundaries ---------------------------------------------
    @staticmethod
    def _windows_state(keep_display_on: bool, release: bool = False) -> bool:  # pragma: no cover - Win32
        try:
            import ctypes

            if release:
                flags = ES_CONTINUOUS
            else:
                flags = ES_CONTINUOUS | ES_SYSTEM_REQUIRED
                if keep_display_on:
                    flags |= ES_DISPLAY_REQUIRED
            # 回傳 0 代表失敗；不檢查的話會以為已經開著，其實螢幕照樣會睡。
            # A zero return means it failed; unchecked, this would report success
            # while the display goes on sleeping anyway.
            return bool(ctypes.windll.kernel32.SetThreadExecutionState(ctypes.c_uint(flags)))
        except Exception as error:
            front_engine_logger.warning(f"[KeepAwake] SetThreadExecutionState failed: {error!r}")
            return False

    def _start_helper(self) -> bool:  # pragma: no cover - process boundary
        command = helper_command()
        if command is None:
            return False
        try:
            self._process = subprocess.Popen(  # nosec B603 # nosemgrep - literal argv, shell=False
                command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL, shell=False)
            return True
        except OSError as error:
            front_engine_logger.warning(f"[KeepAwake] helper failed: {error!r}")
            self._process = None
            return False

    def _stop_helper(self) -> None:  # pragma: no cover - process boundary
        process = self._process
        self._process = None
        if process is None:
            return
        try:
            process.terminate()
            process.wait(timeout=5)
        except Exception as error:
            front_engine_logger.warning(f"[KeepAwake] helper stop failed: {error!r}")
