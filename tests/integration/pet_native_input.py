"""Windows native-message probe for pet-manager keyboard navigation.

Run with an absolute output directory. The probe re-launches itself on a separate,
hidden Win32 desktop, so its windows can be activated (Qt routes keys to the active
window's focus widget) without touching the user's input desktop, foreground or
cursor. Real WM_KEYDOWN / WM_KEYUP / WM_CHAR messages then go through Qt's Windows
message path to the probe's own windows only.

Petting strokes cannot be checked this way: Windows tracks the real pointer and
sends a leave for every posted move while no physical pointer is over the pet,
which ends the gesture. That check needs a person moving the mouse.
"""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import sys
import tempfile
import traceback

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QImage
from PySide6.QtWidgets import QApplication

WM_KEYDOWN, WM_KEYUP, WM_CHAR = 0x0100, 0x0101, 0x0102
VK_TAB, VK_SPACE = 0x09, 0x20

user32 = ctypes.WinDLL('user32', use_last_error=True)
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]


def _settle(app, ms: int = 60) -> None:
    """Run the event loop briefly: Qt queues window-system input and delivers it a pass later."""
    from PySide6.QtCore import QEventLoop
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def _post_key(hwnd: int, key: int) -> None:
    user32.PostMessageW(hwnd, WM_KEYDOWN, key, 1)
    if key == VK_SPACE:
        user32.PostMessageW(hwnd, WM_CHAR, 0x20, 1)
    user32.PostMessageW(hwnd, WM_KEYUP, key, 0xC0000001)


def _cursor() -> list[int]:
    point = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(point))
    return [point.x, point.y]


def _offscreen(app, widget) -> None:
    widget.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
    widget.move(max(screen.geometry().right() for screen in app.screens()) + 1024, 0)


def _sprite(folder: Path) -> str:
    image = QImage(128, 128, QImage.Format.Format_ARGB32)
    image.fill(QColor(240, 96, 42))
    path = folder / 'pet.png'
    image.save(str(path))
    return str(path)


class Probe:
    def __init__(self, app, output: Path, folder: Path) -> None:
        from frontengine.show.pet.desktop_pet import DesktopPetWidget
        from frontengine.ui.page.pet.pet_setting_ui import PetSettingUI
        from frontengine.user_setting.pet_profiles import PetProfiles
        self.app, self.output = app, output
        self.result = {'status': 'failed', 'platform': app.platformName()}
        self.foreground, self.cursors = [], []
        profiles = PetProfiles({}, lambda: None)
        self.pet = DesktopPetWidget(_sprite(folder), profiles=profiles, talk=False, sit_on_windows=False)
        self.page = PetSettingUI()
        self.page.profile_controls.profiles = profiles
        for widget in (self.pet, self.page):
            _offscreen(app, widget)
        self.pet.motion.settled = True

    def observe(self) -> None:
        self.foreground.append(int(user32.GetForegroundWindow() or 0))
        self.cursors.append(_cursor())

    def start(self) -> None:
        self.page.show()
        self.pet.show()
        self.page.pet_list.append(self.pet)
        self.page.profile_controls.refresh(selected=self.pet.profile_session.identifier)
        QTimer.singleShot(800, self.keyboard)

    def keyboard(self) -> None:
        """Tab through the whole manager with real key messages, then pick and run commands."""
        controls = self.page.profile_controls
        self.page.activateWindow()  # only the probe's own hidden desktop changes
        _settle(self.app)
        assert self.page.isActiveWindow(), 'The probe page could not be activated on its desktop'
        hwnd = int(self.page.winId())
        controls.selector.setFocus()
        visited = []
        for _ in range(150):
            visited.append(self._tab(hwnd))
            if visited[-1] is controls.selector:
                break
        # Secondary commands live in "More actions" menus; their menu buttons take focus.
        required = {'selector': controls.selector, 'name': controls.name, 'interaction': controls.interaction,
                    'interact': controls.interact_button, 'wardrobe': controls.wardrobe_button,
                    'customize_menu': controls.customize_button.parent(),
                    'recover_menu': controls.recover_button.parent()}
        missing = [name for name, widget in required.items() if widget not in visited]
        self.result.update(tab_cycle_length=len(visited), tab_cycle_closed=visited[-1] is controls.selector)
        assert not missing, f'Tab never reached: {missing}'
        self._run_from_keyboard(controls, 'greet')
        assert self.pet.profile_session.companion.action == 'greet', 'Space did not run the greeting'
        self.pet.profile_session.advance(1)
        shown = []
        self.pet.show_status = lambda: shown.append(True)
        self._run_from_keyboard(controls, 'cmd:status')
        assert shown == [True], 'The pet menu command did not run from the keyboard'
        recovered = []
        controls.recover_selected = lambda: recovered.append(True)
        controls.recover_button.clicked.disconnect()
        controls.recover_button.clicked.connect(lambda: controls.recover_selected())
        self._menu_command(controls.recover_button)
        assert recovered == [True], 'The overflow menu command did not run from the keyboard'
        self.result.update(keyboard_greet=True, keyboard_pet_command=True, keyboard_menu_command=True)
        self.finish()

    def _menu_command(self, target) -> None:
        """Open the target's overflow menu with Space, walk to it with arrows, press Return."""
        menu_button = target.parent()
        action = next(action for button, action in menu_button._commands if button is target)
        menu_button.setFocus()
        _settle(self.app)

        def choose():
            popup = self.app.activePopupWidget()
            assert popup is not None, 'Space did not open the overflow menu'
            for _ in range(len(popup.actions()) + 1):
                if popup.activeAction() is action:
                    break
                _post_key(int(popup.winId()), 0x28)  # VK_DOWN
                _settle(self.app, 60)
            _post_key(int(popup.winId()), 0x0D)  # VK_RETURN
        QTimer.singleShot(300, choose)
        _post_key(int(self.page.winId()), VK_SPACE)
        _settle(self.app, 1500)

    def _tab(self, hwnd: int):
        """Post one Tab and wait until Qt has delivered it and focus has moved."""
        before = self.page.focusWidget()
        _post_key(hwnd, VK_TAB)
        for _ in range(20):
            _settle(self.app, 25)
            if self.page.focusWidget() is not before:
                break
        return self.page.focusWidget()

    def _run_from_keyboard(self, controls, command: str) -> None:
        """Choose a list entry with arrow keys, Tab to Interact and press Space."""
        hwnd = int(self.page.winId())
        controls.interaction.setFocus()
        _settle(self.app)
        target = controls.interaction.findData(command)
        key = 0x28 if controls.interaction.currentIndex() < target else 0x26  # VK_DOWN / VK_UP
        for _ in range(controls.interaction.count()):
            if controls.interaction.currentIndex() == target:
                break
            index = controls.interaction.currentIndex()
            _post_key(hwnd, key)
            for _ in range(20):
                _settle(self.app, 25)
                if controls.interaction.currentIndex() != index:
                    break
        assert controls.interaction.currentData() == command, f'Arrow keys did not reach {command}'
        for _ in range(60):
            if self.page.focusWidget() is controls.interact_button:
                break
            self._tab(hwnd)
        _post_key(hwnd, VK_SPACE)
        _settle(self.app, 200)

    def finish(self, error=None) -> None:
        if error is not None:
            self.result['error'] = repr(error)
            self.result['traceback'] = traceback.format_exc()
        else:
            own = {int(self.page.winId()), int(self.pet.winId())}
            assert not own.intersection(self.foreground), 'A probe window took the foreground'
            self.result.update(status='passed', foreground_samples=len(self.foreground),
                               cursor_positions=len({tuple(point) for point in self.cursors}))
        self.poll.stop()
        self.pet.close()
        self.page.close()
        (self.output / 'result.json').write_text(json.dumps(self.result, indent=2), encoding='utf-8')
        self.app.quit()


DESKTOP = 'FrontEnginePetInputProbe'


def _launch_on_hidden_desktop(output: Path) -> int:
    """Run this probe in a child process whose windows live on a new desktop."""
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    user32.CreateDesktopW.restype = wintypes.HANDLE
    desktop = user32.CreateDesktopW(DESKTOP, None, None, 0, 0x10000000, None)
    if not desktop:
        raise ctypes.WinError(ctypes.get_last_error())

    class StartupInfo(ctypes.Structure):
        _fields_ = [('cb', wintypes.DWORD), ('lpReserved', wintypes.LPWSTR), ('lpDesktop', wintypes.LPWSTR),
                    ('lpTitle', wintypes.LPWSTR)] + [(name, wintypes.DWORD) for name in (
                        'dwX', 'dwY', 'dwXSize', 'dwYSize', 'dwXCountChars', 'dwYCountChars',
                        'dwFillAttribute', 'dwFlags')] + [('wShowWindow', wintypes.WORD), ('cbReserved2', wintypes.WORD),
                                                          ('lpReserved2', ctypes.c_void_p), ('hStdInput', wintypes.HANDLE),
                                                          ('hStdOutput', wintypes.HANDLE), ('hStdError', wintypes.HANDLE)]

    class ProcessInfo(ctypes.Structure):
        _fields_ = [('hProcess', wintypes.HANDLE), ('hThread', wintypes.HANDLE),
                    ('dwProcessId', wintypes.DWORD), ('dwThreadId', wintypes.DWORD)]

    startup, process = StartupInfo(), ProcessInfo()
    startup.cb = ctypes.sizeof(StartupInfo)
    startup.lpDesktop = DESKTOP
    command = ctypes.create_unicode_buffer(f'"{sys.executable}" "{Path(__file__).resolve()}" "{output}" --child')
    try:
        if not kernel32.CreateProcessW(None, command, None, None, False, 0, None, None,
                                       ctypes.byref(startup), ctypes.byref(process)):
            raise ctypes.WinError(ctypes.get_last_error())
        kernel32.WaitForSingleObject(process.hProcess, 180000)
        code = wintypes.DWORD()
        kernel32.GetExitCodeProcess(process.hProcess, ctypes.byref(code))
        kernel32.CloseHandle(process.hThread)
        kernel32.CloseHandle(process.hProcess)
        return code.value
    finally:
        user32.CloseDesktop(desktop)


def main() -> int:
    output = Path(sys.argv[1]).resolve()
    if '--child' not in sys.argv:
        return _launch_on_hidden_desktop(output)
    output.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    if app.platformName() != 'windows':
        raise RuntimeError('This probe requires the native Windows Qt platform')
    with tempfile.TemporaryDirectory(prefix='frontengine-native-input-') as folder:
        probe = Probe(app, output, Path(folder))
        probe.poll = QTimer()
        probe.poll.timeout.connect(probe.observe)
        probe.poll.start(50)
        for step in ('keyboard',):
            original = getattr(probe, step)

            def guarded(original=original):
                try:
                    original()
                except Exception as error:  # every failure is reported in result.json
                    probe.finish(error)
            setattr(probe, step, guarded)
        probe.observe()
        probe.start()
        app.exec()
    return 0 if probe.result['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
