"""Render a real Imervue asset through the FrontEngine-owned native pet window.

Run on a desktop with an installed puppet extra; pass the reference .puppet path.
"""
import json
import sys
from pathlib import Path

import numpy as np
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from frontengine.show.pet.puppet_pet import PuppetPetWidget


def main() -> None:
    asset = Path(sys.argv[1])
    app = QApplication.instance() or QApplication([])
    pet = PuppetPetWidget(asset, size=(240, 360))
    pet.show()
    result = {}
    def verify():
        frame = pet.canvas.grabFramebuffer()
        if frame.isNull() or not pet.canvas.isValid():
            result['error'] = 'No valid OpenGL puppet frame'
        else:
            rgba = frame.convertToFormat(frame.Format.Format_RGBA8888)
            pixels = np.frombuffer(rgba.bits(), dtype=np.uint8).reshape(rgba.height(), rgba.bytesPerLine())
            if not np.any(pixels[:, 3:rgba.width() * 4:4]):
                result['error'] = 'Puppet frame contains no visible pixels'
            else:
                result.update(status='passed', size=[frame.width(), frame.height()],
                              drawables=len(pet.canvas.document().drawables))
        pet.close()
        app.quit()
    QTimer.singleShot(1500, verify)
    app.exec()
    print(json.dumps(result))
    if 'error' in result:
        raise RuntimeError(result['error'])


if __name__ == '__main__':
    main()
