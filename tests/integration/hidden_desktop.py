"""Run a probe in a child process on its own hidden Win32 desktop.

Windows on that desktop use the real monitors' geometry, work areas and GPU, and
can be activated, but none of it reaches the user's input desktop: their
foreground window, cursor and screen contents are never touched.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
from pathlib import Path
import sys

DESKTOP = 'FrontEnginePetProbe'
CHILD_FLAG = '--child'


class _StartupInfo(ctypes.Structure):
    _fields_ = [('cb', wintypes.DWORD), ('lpReserved', wintypes.LPWSTR), ('lpDesktop', wintypes.LPWSTR),
                ('lpTitle', wintypes.LPWSTR)] + [(name, wintypes.DWORD) for name in (
                    'dwX', 'dwY', 'dwXSize', 'dwYSize', 'dwXCountChars', 'dwYCountChars', 'dwFillAttribute',
                    'dwFlags')] + [('wShowWindow', wintypes.WORD), ('cbReserved2', wintypes.WORD),
                                   ('lpReserved2', ctypes.c_void_p), ('hStdInput', wintypes.HANDLE),
                                   ('hStdOutput', wintypes.HANDLE), ('hStdError', wintypes.HANDLE)]


class _ProcessInfo(ctypes.Structure):
    _fields_ = [('hProcess', wintypes.HANDLE), ('hThread', wintypes.HANDLE),
                ('dwProcessId', wintypes.DWORD), ('dwThreadId', wintypes.DWORD)]


def is_child(output: Path | None = None) -> bool:
    """True in the child; it then sends stderr and fatal tracebacks to output/stderr.txt."""
    if CHILD_FLAG not in sys.argv:
        return False
    if output is not None:
        import faulthandler
        import os
        sys.stderr = open(Path(output) / 'stderr.txt', 'w', encoding='utf-8', buffering=1)
        os.dup2(sys.stderr.fileno(), 2)  # Qt's own fatal messages go to the C-level stderr
        faulthandler.enable(sys.stderr)
    return True


def run_on_hidden_desktop(script: str | Path, *args: str, timeout_ms: int = 300000) -> int:
    """Start ``python script *args --child`` on a fresh desktop and return its exit code."""
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    user32.CreateDesktopW.restype = wintypes.HANDLE
    user32.CloseDesktop.argtypes = [wintypes.HANDLE]
    kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel32.WaitForSingleObject.restype = wintypes.DWORD
    kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    desktop = user32.CreateDesktopW(DESKTOP, None, None, 0, 0x10000000, None)
    if not desktop:
        raise ctypes.WinError(ctypes.get_last_error())
    startup, process = _StartupInfo(), _ProcessInfo()
    startup.cb = ctypes.sizeof(_StartupInfo)
    startup.lpDesktop = DESKTOP
    quoted = ' '.join(f'"{part}"' for part in (sys.executable, str(Path(script).resolve()), *args, CHILD_FLAG))
    command = ctypes.create_unicode_buffer(quoted)
    try:
        if not kernel32.CreateProcessW(None, command, None, None, False, 0, None, None,
                                       ctypes.byref(startup), ctypes.byref(process)):
            raise ctypes.WinError(ctypes.get_last_error())
        if kernel32.WaitForSingleObject(process.hProcess, timeout_ms) != 0:
            kernel32.TerminateProcess(process.hProcess, 124)  # a hung probe must not linger unseen
            kernel32.WaitForSingleObject(process.hProcess, 5000)
        code = wintypes.DWORD()
        kernel32.GetExitCodeProcess(process.hProcess, ctypes.byref(code))
        kernel32.CloseHandle(process.hThread)
        kernel32.CloseHandle(process.hProcess)
        return code.value
    finally:
        user32.CloseDesktop(desktop)
