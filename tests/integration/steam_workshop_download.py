"""Verify an owned private test item, download it, and load its scene in real Qt."""
from __future__ import annotations

import argparse
import ctypes as c
import json
import os
import tempfile
from pathlib import Path

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from frontengine.show.scene.scene import SceneManager
from frontengine.utils.scene_format.scene_package import load_package
from frontengine.utils.steam.steam_runtime import APP_ID, DetailsResult, PACK, SteamRuntime, I32, U64
from frontengine.utils.workshop.workshop_cache import WorkshopCache
from frontengine.utils.workshop.workshop_publications import item_id
from frontengine.utils.workshop.workshop_service import WorkshopService
from frontengine.utils.workshop.workshop_subscriptions import WorkshopSubscriptions


class SubscriptionResult(c.Structure):
    _pack_ = PACK
    _fields_ = [("result", I32), ("item_id", U64)]


def await_call(service, callback: int, structure, function: str, *arguments):
    result = []
    loop, timeout = QEventLoop(), QTimer()
    timeout.setSingleShot(True)
    timeout.timeout.connect(loop.quit)
    handle = service.backend.call(function, *arguments)
    if not handle:
        raise RuntimeError(f"Steam rejected {function}")
    def received(event):
        if event.call_handle == handle:
            if event.callback == callback and not event.failed and len(event.payload) == c.sizeof(structure):
                result.append(structure.from_buffer_copy(event.payload))
            loop.quit()
    service.event_received.connect(received)
    try:
        timeout.start(120000)
        loop.exec()
    finally:
        timeout.stop()
        service.event_received.disconnect(received)
    if not result:
        raise RuntimeError(f"Steam did not confirm {function}")
    return result[0]


def download(service, cache, published_id: str) -> dict:
    loop, timeout = QEventLoop(), QTimer()
    timeout.setSingleShot(True)
    timeout.timeout.connect(loop.quit)
    subscriptions = WorkshopSubscriptions(service, cache)
    result = []
    def changed(items):
        for item in items:
            if item["id"] == published_id and item["status"] in ("ready", "invalid", "failed", "conflict"):
                result.append(item)
                loop.quit()
    subscriptions.changed.connect(changed)
    subscriptions.refresh()
    try:
        if not result:
            timeout.start(180000)
            loop.exec()
        if not result or result[0]["status"] != "ready":
            raise ValueError("Subscription was not ready: " + json.dumps(result))
        return result[0]
    finally:
        timeout.stop()
        subscriptions.stop()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--item-id", required=True)
    parser.add_argument("--storage", type=Path, required=True)
    parser.add_argument("--development", action="store_true")
    args = parser.parse_args()
    published_id, storage = str(item_id(args.item_id)), args.storage.absolute()
    app = QApplication.instance() or QApplication([])
    service = WorkshopService(backend=SteamRuntime())
    previous = Path.cwd()
    subscribed_here = False
    with tempfile.TemporaryDirectory(prefix="frontengine-steam-download-") as directory:
        try:
            if args.development:
                os.chdir(directory)
                Path("steam_appid.txt").write_text(str(APP_ID), encoding="ascii")
            if not service.start():
                raise RuntimeError(service.backend.reason)
            details = await_call(service, 3402, DetailsResult, "RequestUGCDetails", int(published_id), 0).details
            if (details.result != 1 or details.owner != service.backend.user_id or
                    details.consumer_app != APP_ID or details.visibility != 2):
                raise ValueError("The test item must belong to this account/App and be private")
            subscribed = {item["id"] for item in service.backend.subscribed_items()}
            if published_id not in subscribed:
                result = await_call(service, 1313, SubscriptionResult, "SubscribeItem", int(published_id))
                if result.result != 1 or result.item_id != int(published_id):
                    raise ValueError(f"Steam subscription failed: {result.result}")
                subscribed_here = True
            cache = WorkshopCache(service.backend.user_id, storage)
            ready = download(service, cache, published_id)
            entries, lease = load_package(cache.entry(ready))
            scene = SceneManager()
            try:
                for entry in entries.values():
                    getattr(scene, "add_" + entry["type"].lower())(entry)
                app.processEvents()
                if not scene.widget_list:
                    raise ValueError("Downloaded scene did not create renderable layers")
                frames = [proxy.widget().output_frame() for proxy in scene.widget_list]
                if not all(not frame.isNull() for frame in frames):
                    raise ValueError("Downloaded scene produced an empty frame")
                print(json.dumps({"item_id": published_id, "visibility": "private",
                                  "status": ready["status"], "scene_layers": len(entries),
                                  "rendered_frames": len(frames)}))
            finally:
                scene.clear()
                lease.cleanup()
            return 0
        finally:
            try:
                if subscribed_here and service.backend.initialized:
                    result = await_call(service, 1315, SubscriptionResult, "UnsubscribeItem", int(published_id))
                    if result.result != 1:
                        print(json.dumps({"cleanup": "unsubscribe_failed", "result": result.result}))
            finally:
                service.stop()
                os.chdir(previous)


if __name__ == "__main__":
    raise SystemExit(main())
