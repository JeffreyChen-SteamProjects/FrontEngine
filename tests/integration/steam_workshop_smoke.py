"""Explicit read-only native Steam check; never creates or updates Workshop items."""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from frontengine.utils.steam.steam_runtime import APP_ID, SteamRuntime


def main() -> int:
    """Initialize, pump callbacks and list subscription availability, then shut down."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path)
    parser.add_argument("--development", action="store_true")
    arguments = parser.parse_args()
    runtime = SteamRuntime(arguments.runtime)
    previous = Path.cwd()
    with tempfile.TemporaryDirectory(prefix="frontengine-steam-smoke-") as directory:
        try:
            if arguments.development:
                os.chdir(directory)
                Path("steam_appid.txt").write_text(str(APP_ID), encoding="ascii")
            available = runtime.initialize()
            result = {"available": available, "reason": runtime.reason}
            if available:
                result.update(runtime.diagnostics())
                result["subscription_count"] = len(runtime.subscribed_items())
                result["callbacks_processed"] = len(runtime.poll())
            print(json.dumps(result, ensure_ascii=False))
            return 0 if available else 2
        finally:
            runtime.shutdown()
            os.chdir(previous)


if __name__ == "__main__":
    raise SystemExit(main())
