"""
開機自動啟動：Windows 寫 HKCU 的 Run 登錄機碼，Linux 放 XDG autostart 的 .desktop，
macOS 放 LaunchAgents 的 plist。全部只碰目前使用者的設定，不需要管理員權限，
也不新增相依套件；產生內容的部分是純函式，方便測試。

Start FrontEngine with the session: an HKCU Run value on Windows, an XDG
autostart .desktop on Linux, a LaunchAgent plist on macOS. Everything stays in
the current user's own configuration — no elevation, no new dependencies — and
the content builders are pure so they can be tested on any platform.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional

from frontengine.utils.logging.loggin_instance import front_engine_logger

APP_NAME = "FrontEngine"
LAUNCH_AGENT_LABEL = "com.frontengine.autostart"
_DESKTOP_FILE = "frontengine.desktop"


def escape_xml(text) -> str:
    """
    跳脫 plist 需要的三個字元。這裡只產生輸出、不解析任何 XML，所以不引入
    XML 解析器（也就沒有 XXE 那類疑慮）。
    Escape the three characters a plist needs. This only writes XML — nothing
    here parses it — so no XML parser is pulled in.
    """
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def launch_command() -> List[str]:
    """
    回傳能重新啟動本程式的命令：打包成執行檔時就是執行檔本身，
    否則以目前的直譯器執行 `-m frontengine`。
    The command that relaunches the app: the frozen executable when packaged,
    otherwise the current interpreter running ``-m frontengine``.
    """
    if getattr(sys, "frozen", False):
        return [sys.executable]
    return [sys.executable, "-m", "frontengine"]


def quote_command(command: List[str]) -> str:
    """把命令組成一行字串，含空白的項目加上引號。"""
    parts = []
    for part in command:
        text = str(part)
        parts.append(f'"{text}"' if " " in text and not text.startswith('"') else text)
    return " ".join(parts)


def desktop_entry_text(command: List[str], app_name: str = APP_NAME) -> str:
    """產生 XDG autostart 用的 .desktop 內容。"""
    return (
        "[Desktop Entry]\n"
        "Type=Application\n"
        f"Name={app_name}\n"
        f"Exec={quote_command(command)}\n"
        "X-GNOME-Autostart-enabled=true\n"
        "Terminal=false\n"
    )


def launch_agent_plist(command: List[str], label: str = LAUNCH_AGENT_LABEL) -> str:
    """產生 macOS LaunchAgent 用的 plist 內容。"""
    arguments = "".join(f"        <string>{escape_xml(part)}</string>\n" for part in command)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
        '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        '<plist version="1.0">\n'
        "<dict>\n"
        "    <key>Label</key>\n"
        f"    <string>{escape_xml(label)}</string>\n"
        "    <key>ProgramArguments</key>\n"
        "    <array>\n"
        f"{arguments}"
        "    </array>\n"
        "    <key>RunAtLoad</key>\n"
        "    <true/>\n"
        "</dict>\n"
        "</plist>\n"
    )


def autostart_path() -> Optional[Path]:
    """回傳本平台放置自動啟動設定的檔案路徑；Windows 用登錄檔，回傳 None。"""
    if sys.platform == "win32":
        return None
    if sys.platform == "darwin":
        return Path.home() / "Library" / "LaunchAgents" / f"{LAUNCH_AGENT_LABEL}.plist"
    return Path.home() / ".config" / "autostart" / _DESKTOP_FILE


def is_enabled() -> bool:
    """目前是否已設定開機自動啟動。"""
    if sys.platform == "win32":
        return _read_windows_run_value() is not None
    path = autostart_path()
    return bool(path and path.is_file())


def set_enabled(enabled: bool) -> bool:
    """
    開啟或關閉開機自動啟動；成功回傳 True，失敗記錄後回傳 False（不丟例外）。
    Enable or disable autostart. Returns False (logged) instead of raising.
    """
    front_engine_logger.info(f"[autostart] set_enabled | enabled={enabled}")
    try:
        if sys.platform == "win32":
            return _set_windows(enabled)
        return _set_file(enabled)
    except (OSError, ValueError) as error:
        front_engine_logger.warning(f"[autostart] failed: {error!r}")
        return False


def _set_file(enabled: bool) -> bool:
    path = autostart_path()
    if path is None:
        return False
    if not enabled:
        if path.is_file():
            path.unlink()
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    command = launch_command()
    content = launch_agent_plist(command) if sys.platform == "darwin" else desktop_entry_text(command)
    path.write_text(content, encoding="utf-8")
    return True


def _run_key():
    import winreg

    return winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0,
        winreg.KEY_READ | winreg.KEY_WRITE,
    )


def _read_windows_run_value() -> Optional[str]:
    try:
        import winreg

        with _run_key() as key:
            value, _kind = winreg.QueryValueEx(key, APP_NAME)
            return str(value)
    except FileNotFoundError:
        return None
    except Exception as error:  # pragma: no cover - registry boundary
        front_engine_logger.debug(f"[autostart] registry read failed: {error!r}")
        return None


def _set_windows(enabled: bool) -> bool:
    import winreg

    with _run_key() as key:
        if enabled:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, quote_command(launch_command()))
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
    return True
