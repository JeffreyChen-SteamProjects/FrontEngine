"""Windows entry point sharing the published CLI and explicit packaged acceptance."""
from __future__ import annotations
import sys


def main() -> None:
    """Isolate acceptance settings before importing the application."""
    if '--verify-scene-build' in sys.argv:
        from scene_build_acceptance import main as verify
        sys.exit(verify(sys.argv[1:]))
    from frontengine.ui.main_ui import main as launch
    launch()


if __name__ == '__main__':
    main()
