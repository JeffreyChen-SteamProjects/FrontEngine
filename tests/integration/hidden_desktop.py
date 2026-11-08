"""Run a probe in a child process on its own hidden Win32 desktop.

Windows on that desktop use the real monitors' geometry, work areas and GPU.
The launcher assigns the child to that desktop without switching the input
desktop. Probe code must still avoid global input injection and desktop switches.
Before/after foreground and cursor samples do not identify the cause of changes.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
from pathlib import Path
import sys

DESKTOP = 'FrontEnginePetProbe'
CHILD_FLAG = '--child'
DESKTOP_READOBJECTS = 0x0001
UOI_NAME = 2


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
    """Enter a child probe only on a desktop separate from the input desktop."""
    if CHILD_FLAG not in sys.argv:
        return False
    if output is not None:
        import faulthandler
        import os
        sys.stderr = open(Path(output) / 'stderr.txt', 'w', encoding='utf-8', buffering=1)
        os.dup2(sys.stderr.fileno(), 2)  # Qt's own fatal messages go to the C-level stderr
        faulthandler.enable(sys.stderr)
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    user32.GetThreadDesktop.argtypes = [wintypes.DWORD]
    user32.GetThreadDesktop.restype = wintypes.HANDLE
    user32.OpenInputDesktop.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    user32.OpenInputDesktop.restype = wintypes.HANDLE
    user32.CloseDesktop.argtypes = [wintypes.HANDLE]
    user32.GetUserObjectInformationW.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p,
                                               wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    kernel32.GetCurrentThreadId.restype = wintypes.DWORD
    input_desktop = user32.OpenInputDesktop(0, False, DESKTOP_READOBJECTS)
    if not input_desktop:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        names = []
        for handle in (user32.GetThreadDesktop(kernel32.GetCurrentThreadId()), input_desktop):
            name = ctypes.create_unicode_buffer(512)
            needed = wintypes.DWORD()
            if not user32.GetUserObjectInformationW(handle, UOI_NAME, name, ctypes.sizeof(name), ctypes.byref(needed)):
                raise ctypes.WinError(ctypes.get_last_error())
            names.append(name.value)
    finally:
        user32.CloseDesktop(input_desktop)
    if output is not None:
        import json
        (Path(output) / 'desktop.json').write_text(json.dumps(
            {'thread_desktop': names[0], 'input_desktop': names[1]}, indent=2), encoding='utf-8')
    if names[0] == names[1]:
        raise RuntimeError('Refusing to run a probe on the input desktop')
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
