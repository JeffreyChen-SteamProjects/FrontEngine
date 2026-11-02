"""Real-monitor acceptance for ordinary overlays crossing between monitors with different scaling.

Usage (Windows, two monitors with different scale factors, from the repository root)::

    py tests/integration/overlay_mixed_dpi_native.py OUTPUT_DIR

The probe re-launches itself on a hidden Win32 desktop (see hidden_desktop.py), so the
user's windows are never touched, and runs from a temporary working directory, so the
user's settings are not either. On the real monitors it shows an image, a GIF, a text
overlay, a sticky note and a pinned image, then for each one:

* moves it from the 100% monitor onto the scaled one and back (as a program or a
  remembered position would), and
* drags it across the boundary with real WM_LBUTTONDOWN / WM_MOUSEMOVE / WM_LBUTTONUP
  messages after unlocking it, as a person would,

and checks after each crossing that it is on the new monitor, still shown, inside that
monitor, at its own logical size, and that Windows' physical size matches size x scale.
Writes OUTPUT_DIR/result.json and exits non-zero on failure.
"""
from __future__ import annotations

import ctypes
import json
import sys
import tempfile
import traceback
from ctypes import wintypes
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))  # test this checkout, never an installed frontengine
sys.path.insert(0, str(Path(__file__).resolve().parent))

WM_MOUSEMOVE, WM_LBUTTONDOWN, WM_LBUTTONUP, MK_LBUTTON = 0x0200, 0x0201, 0x0202, 0x0001
SIZE = (360, 240)


def _user32():
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    return user32


def _physical(user32, hwnd: int) -> list:
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return [rect.right - rect.left, rect.bottom - rect.top]


def _rect(rect) -> list:
    return [rect.x(), rect.y(), rect.width(), rect.height()]


class Probe:
    def __init__(self, app, output: Path, folder: Path) -> None:
        self.app, self.output, self.folder = app, output, folder
        self.user32 = _user32()
        self.result = {"status": "failed", "platform": app.platformName(), "checks": [], "problems": []}
        self.overlays = []

    # ----- set-up ---------------------------------------------------------------------------

    def screens(self):
        screens = self.app.screens()
        self.result["screens"] = [[s.name(), s.devicePixelRatio(), _rect(s.geometry()), _rect(s.availableGeometry())]
                                  for s in screens]
        plain = [s for s in screens if s.devicePixelRatio() == 1.0]
        scaled = [s for s in screens if s.devicePixelRatio() != 1.0]
        if not plain or not scaled:
            raise RuntimeError("Needs one monitor at 100% and one at another scale")
        return plain[0], scaled[0]

    def _files(self) -> tuple[Path, Path]:
        from PIL import Image
        picture = self.folder / "picture.png"
        Image.new("RGBA", SIZE, (240, 120, 40, 255)).save(picture)
        animation = self.folder / "animation.gif"
        frames = [Image.new("RGB", SIZE, color) for color in ((40, 120, 240), (240, 200, 40))]
        frames[0].save(animation, save_all=True, append_images=frames[1:], duration=120, loop=0)
        return picture, animation

    def build(self):
        from PySide6.QtGui import QPixmap
        from frontengine.show.gif.paint_gif import GifWidget
        from frontengine.show.image.paint_image import ImageWidget
        from frontengine.show.notes.sticky_note_widget import StickyNoteWidget
        from frontengine.show.pinned.pinned_image import PinnedImageWidget
        from frontengine.show.text.draw_text import TextWidget
        picture, animation = self._files()
        text = TextWidget("FrontEngine")
        text.resize(*SIZE)
        made = [ImageWidget(str(picture)), GifWidget(str(animation)), text,
                StickyNoteWidget("note", width=SIZE[0], height=SIZE[1]),
                PinnedImageWidget(QPixmap(str(picture)))]
        for overlay in made:
            if hasattr(overlay, "set_ui_window_flag"):
                overlay.set_ui_window_flag()
                overlay.set_ui_variable(1.0)
            if hasattr(overlay, "overlay_remembers_geometry"):
                overlay.overlay_remembers_geometry = False       # no shared remembered rect between runs
            self.overlays.append((type(overlay).__name__, overlay, (overlay.width(), overlay.height())))
        return made

    # ----- checks -----------------------------------------------------------------------------

    def check(self, name: str, overlay, size, screen, how: str) -> None:
        ratio = screen.devicePixelRatio()
        physical = _physical(self.user32, int(overlay.winId()))
        entry = {"overlay": name, "how": how, "target": screen.name(), "ratio": ratio,
                 "screen": overlay.screen().name(), "visible": overlay.isVisible(),
                 "logical": [overlay.width(), overlay.height()], "expected": list(size),
                 "geometry": _rect(overlay.geometry()), "physical": physical}
        problems = []
        if overlay.screen().name() != screen.name():
            problems.append("not on the target monitor")
        if not overlay.isVisible():
            problems.append("hidden")
        if not screen.geometry().contains(overlay.geometry()):
            problems.append("not inside the monitor")
        if (overlay.width(), overlay.height()) != tuple(size):
            problems.append("logical size changed")
        if abs(physical[0] - round(overlay.width() * ratio)) > 2 or abs(physical[1] - round(overlay.height() * ratio)) > 2:
            problems.append("physical size does not match logical size x scale")
        entry["problems"] = problems
        self.result["checks"].append(entry)
        self.result["problems"] += [f"{name} {how} -> {screen.name()}: {p}" for p in problems]

    # ----- steps (each yield is a wait in ms) ---------------------------------------------------

    def place(self, overlay, screen):
        area = screen.availableGeometry()
        overlay.move(area.center().x() - overlay.width() // 2, area.center().y() - overlay.height() // 2)

    def moved(self):
        """Move each overlay to the scaled monitor and back, as a remembered position would."""
        plain, scaled = self.screens()
        for overlay in [entry[1] for entry in self.overlays]:
            overlay.setScreen(plain)
            self.place(overlay, plain)
            overlay.show()
        yield 800
        for name, overlay, size in self.overlays:
            for screen in (scaled, plain, scaled):
                self.place(overlay, screen)
                yield 700
                self.check(name, overlay, size, screen, "move")

    def dragged(self):
        """Drag each overlay across the boundary with real mouse messages, after unlocking it."""
        from frontengine.show.window_helpers import set_overlay_locked
        plain, scaled = self.screens()
        for name, overlay, size in self.overlays:
            set_overlay_locked(overlay, False)
            overlay.setScreen(plain)
            area = plain.availableGeometry()
            overlay.move(area.left() + 40, area.center().y() - overlay.height() // 2)
            overlay.show()
            yield 600
            direction = 1 if scaled.geometry().x() > plain.geometry().x() else -1
            hwnd, x, y = int(overlay.winId()), overlay.width() // 2, overlay.height() // 2
            self.user32.PostMessageW(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, (y << 16) | x)
            yield 80
            steps = 0
            while overlay.screen().name() != scaled.name() and steps < 200:
                self.user32.PostMessageW(hwnd, WM_MOUSEMOVE, MK_LBUTTON, (y << 16) | ((x + 40 * direction) & 0xFFFF))
                steps += 1
                yield 30
            target = scaled.availableGeometry()
            while not target.contains(overlay.geometry()) and steps < 260:
                self.user32.PostMessageW(hwnd, WM_MOUSEMOVE, MK_LBUTTON, (y << 16) | ((x + 30 * direction) & 0xFFFF))
                steps += 1
                yield 30
            self.user32.PostMessageW(hwnd, WM_LBUTTONUP, 0, (y << 16) | x)
            yield 1200
            self.check(name, overlay, size, scaled, f"drag ({steps} moves)")

    # ----- runner -------------------------------------------------------------------------------

    def run(self, finish) -> None:
        from PySide6.QtCore import QTimer
        steps = [self.moved(), self.dragged()]

        def advance():
            try:
                while steps:
                    try:
                        QTimer.singleShot(next(steps[0]), advance)
                        return
                    except StopIteration:
                        steps.pop(0)
                finish()
            except Exception as error:  # every failure ends up in result.json
                finish(error)
        QTimer.singleShot(0, advance)

    def finish(self, error=None) -> None:
        if self.result.get("finished"):
            return
        self.result["finished"] = True
        if error is not None:
            self.result.update(error=repr(error), traceback=traceback.format_exc())
        elif not self.result["problems"]:
            self.result["status"] = "passed"
        for _name, overlay, _size in self.overlays:
            overlay.close()
        (self.output / "result.json").write_text(json.dumps(self.result, indent=2), encoding="utf-8")
        self.app.quit()


def main() -> int:
    from hidden_desktop import is_child, run_on_hidden_desktop
    output = Path(sys.argv[1]).resolve()
    output.mkdir(parents=True, exist_ok=True)
    if not is_child(output):
        return run_on_hidden_desktop(__file__, str(output))
    import os
    from PySide6.QtCore import QCoreApplication, QEvent, QTimer
    from PySide6.QtWidgets import QApplication
    # The GIF overlay keeps its file open until it is deleted; never fail the run over clean-up.
    with tempfile.TemporaryDirectory(prefix="frontengine-overlay-dpi-", ignore_cleanup_errors=True) as folder:
        os.chdir(folder)                      # settings written while dragging stay in here
        app = QApplication([])
        app.setQuitOnLastWindowClosed(False)
        if app.platformName() != "windows":
            raise RuntimeError("This probe requires the native Windows Qt platform")
        probe = Probe(app, output, Path(folder))
        probe.build()
        probe.run(probe.finish)
        QTimer.singleShot(170000, lambda: probe.finish(TimeoutError("Probe did not finish within 170 seconds")))
        app.exec()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)   # release the files
        os.chdir(REPO)
    return 0 if probe.result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
