"""Explicit private publication/update smoke check; uses the real Steam client."""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from frontengine.utils.steam.steam_runtime import APP_ID, SteamRuntime
from frontengine.utils.workshop.workshop_publications import PublicationStore
from frontengine.utils.workshop.workshop_publisher import WorkshopPublisher
from frontengine.utils.workshop.workshop_service import WorkshopService


def run_operation(publisher: WorkshopPublisher, operation: str) -> dict:
    loop = QEventLoop()
    timer = QTimer()
    timer.setInterval(100)
    timer.timeout.connect(lambda: loop.quit() if not publisher.busy else None)
    publisher.start(operation)
    if publisher.busy:
        timer.start()
        loop.exec()
    timer.stop()
    return dict(publisher.record)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path)
    parser.add_argument("--development", action="store_true")
    parser.add_argument("--kind", choices=["scene", "preset", "pet_pack"], required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--preview", type=Path, required=True)
    parser.add_argument("--storage", type=Path, required=True)
    parser.add_argument("--operation", help="Resume the exact saved operation; never blindly recreate")
    parser.add_argument("--update", action="store_true", help="Update the latest completed private test item")
    arguments = parser.parse_args()
    source, preview, storage = (p.absolute() for p in (arguments.source, arguments.preview, arguments.storage))
    runtime_path = arguments.runtime.absolute() if arguments.runtime else None
    app = QApplication.instance() or QApplication([])
    service = WorkshopService(backend=SteamRuntime(runtime_path))
    previous = Path.cwd()
    with tempfile.TemporaryDirectory(prefix="frontengine-steam-private-") as directory:
        try:
            if arguments.development:
                os.chdir(directory)
                Path("steam_appid.txt").write_text(str(APP_ID), encoding="ascii")
            if not service.start():
                print(json.dumps({"state": "unavailable", "reason": service.backend.reason}))
                return 2
            store = PublicationStore(service.backend.user_id, storage)
            records = store.records(recover=True)
            if arguments.operation:
                record = store.load(arguments.operation)
            else:
                if records and not arguments.update:
                    raise ValueError("A private test operation already exists; specify --operation or --update")
                completed = [r for r in records if r["state"] == "completed" and r["visibility"] == 2]
                if arguments.update and not completed:
                    raise ValueError("No completed private item exists to update")
                published_id = completed[-1]["published_id"] if arguments.update else ""
                record = store.prepare(arguments.kind, source, "FrontEngine Private Integration Test",
                                       preview, "Private automated integration check for FrontEngine.",
                                       ["Scene" if arguments.kind == "scene" else "Pet"], 2, published_id)
            publisher = WorkshopPublisher(service, store)
            result = run_operation(publisher, record["operation"])
            print(json.dumps({key: result[key] for key in ("operation", "published_id", "state", "error")}))
            return 0 if result["state"] == "completed" else 3
        finally:
            service.stop()
            os.chdir(previous)
            app.processEvents()


if __name__ == "__main__":
    raise SystemExit(main())
