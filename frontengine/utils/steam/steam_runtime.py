"""Lazy Steamworks flat-API access and bounded manual callback dispatch."""
from __future__ import annotations

import ctypes as c
import os
import sys
from dataclasses import dataclass
from pathlib import Path

APP_ID = 2793470
U64, U32, I32, PTR = c.c_uint64, c.c_uint32, c.c_int32, c.c_void_p
PACK = 8 if sys.platform == "win32" else 4


class CallbackMessage(c.Structure):
    """Manual-dispatch layout from steam_api_internal.h."""
    _pack_ = PACK
    _fields_ = [("user", I32), ("callback", I32), ("data", PTR), ("size", I32)]


class CallCompleted(c.Structure):
    """SteamAPICallCompleted_t from isteamutils.h."""
    _pack_ = PACK
    _fields_ = [("handle", U64), ("callback", I32), ("size", U32)]


class CreateResult(c.Structure):
    """CreateItemResult_t; retain the published ID even when content upload fails."""
    _pack_ = PACK
    _fields_ = [("result", I32), ("item_id", U64), ("needs_terms", c.c_bool)]


class SubmitResult(c.Structure):
    """SubmitItemUpdateResult_t."""
    _pack_ = PACK
    _fields_ = [("result", I32), ("needs_terms", c.c_bool), ("item_id", U64)]


class ItemDetails(c.Structure):
    """SteamUGCDetails_t from interface 021; lengths match the selected SDK."""
    _pack_ = PACK
    _fields_ = [("item_id", U64), ("result", I32), ("file_type", I32),
                ("creator_app", U32), ("consumer_app", U32), ("title", c.c_char * 129),
                ("description", c.c_char * 8000), ("owner", U64), ("created", U32),
                ("updated", U32), ("added", U32), ("visibility", I32),
                ("banned", c.c_bool), ("accepted", c.c_bool), ("tags_truncated", c.c_bool),
                ("tags", c.c_char * 1025), ("file", U64), ("preview_file", U64),
                ("filename", c.c_char * 260), ("file_size", I32), ("preview_size", I32),
                ("url", c.c_char * 256), ("votes_up", U32), ("votes_down", U32),
                ("score", c.c_float), ("children", U32), ("total_size", U64)]


class DetailsResult(c.Structure):
    """SteamUGCRequestUGCDetailsResult_t."""
    _pack_ = PACK
    _fields_ = [("details", ItemDetails), ("cached", c.c_bool)]


class StringArray(c.Structure):
    """SteamParamStringArray_t passed synchronously to SetItemTags."""
    _pack_ = PACK
    _fields_ = [("strings", c.POINTER(c.c_char_p)), ("count", I32)]


@dataclass(frozen=True)
class SteamEvent:
    """Owned bytes copied before Steam releases its callback memory."""
    callback: int
    payload: bytes
    call_handle: int = 0
    failed: bool = False


BASE_FUNCTIONS = {
    "SteamAPI_InitFlat": (I32, [c.c_char_p]),
    "SteamAPI_Shutdown": (None, []),
    "SteamAPI_GetHSteamPipe": (I32, []),
    "SteamAPI_SteamUGC_v021": (PTR, []),
    "SteamAPI_SteamUtils_v011": (PTR, []),
    "SteamAPI_SteamUser_v023": (PTR, []),
    "SteamAPI_ISteamUtils_GetAppID": (U32, [PTR]),
    "SteamAPI_ISteamUser_GetSteamID": (U64, [PTR]),
    "SteamAPI_ISteamUser_BLoggedOn": (c.c_bool, [PTR]),
    "SteamAPI_SteamRemoteStorage_v016": (PTR, []),
    "SteamAPI_ISteamRemoteStorage_GetQuota": (c.c_bool, [PTR, c.POINTER(U64), c.POINTER(U64)]),
    "SteamAPI_SteamApps_v009": (PTR, []),
    "SteamAPI_ISteamApps_BIsSubscribedApp": (c.c_bool, [PTR, U32]),
    "SteamAPI_ManualDispatch_Init": (None, []),
    "SteamAPI_ManualDispatch_RunFrame": (None, [I32]),
    "SteamAPI_ManualDispatch_GetNextCallback": (c.c_bool, [I32, c.POINTER(CallbackMessage)]),
    "SteamAPI_ManualDispatch_FreeLastCallback": (None, [I32]),
    "SteamAPI_ManualDispatch_GetAPICallResult": (
        c.c_bool, [I32, U64, PTR, I32, I32, c.POINTER(c.c_bool)]),
}
UGC_FUNCTIONS = {
    "RequestUGCDetails": (U64, [U64, U32]),
    "CreateItem": (U64, [U32, I32]),
    "StartItemUpdate": (U64, [U32, U64]),
    "SetItemTitle": (c.c_bool, [U64, c.c_char_p]),
    "SetItemDescription": (c.c_bool, [U64, c.c_char_p]),
    "SetItemMetadata": (c.c_bool, [U64, c.c_char_p]),
    "SetItemContent": (c.c_bool, [U64, c.c_char_p]),
    "SetItemPreview": (c.c_bool, [U64, c.c_char_p]),
    "SetItemVisibility": (c.c_bool, [U64, I32]),
    "SetItemTags": (c.c_bool, [U64, c.POINTER(StringArray), c.c_bool]),
    "SubmitItemUpdate": (U64, [U64, c.c_char_p]),
    "GetItemUpdateProgress": (I32, [U64, c.POINTER(U64), c.POINTER(U64)]),
    "GetNumSubscribedItems": (U32, [c.c_bool]),
    "GetSubscribedItems": (U32, [c.POINTER(U64), U32, c.c_bool]),
    "GetItemState": (U32, [U64]),
    "GetItemInstallInfo": (c.c_bool, [U64, c.POINTER(U64), c.c_char_p, U32, c.POINTER(U32)]),
    "DownloadItem": (c.c_bool, [U64, c.c_bool]),
    "SubscribeItem": (U64, [U64]),
    "UnsubscribeItem": (U64, [U64]),
}


def runtime_path(explicit: str | Path | None = None) -> Path:
    """Select explicit or packaged libraries, without searching the process PATH."""
    if explicit or os.environ.get("FRONTENGINE_STEAM_API"):
        path = Path(explicit or os.environ["FRONTENGINE_STEAM_API"])
        if not path.is_absolute():
            raise ValueError("Steam runtime must be an absolute path")
        return path
    filename = "steam_api64.dll" if sys.platform == "win32" else "libsteam_api.so"
    if sys.platform == "darwin":
        filename = "libsteam_api.dylib"
    packaged = Path(sys.executable).resolve().parent / filename
    if packaged.is_file():
        return packaged
    platform_dir = {"win32": "win64", "darwin": "osx"}.get(sys.platform, "linux64")
    return Path(__file__).resolve().parents[3] / "steam_sdk" / "redistributable_bin" / platform_dir / filename


class SteamRuntime:
    """Own one initialized Steam session; construction has no native side effects."""

    def __init__(self, path: str | Path | None = None, loader=None) -> None:
        self.path = path
        self.loader = loader or c.CDLL
        self.library = None
        self.ugc = self.user = self.utils = self.pipe = 0
        self.user_id = 0
        self.initialized = False
        self.reason = "Steam has not been initialized"

    def initialize(self) -> bool:
        """Validate interfaces and App ID; report unavailability without killing the app."""
        if self.initialized:
            return True
        if sys.platform != "win32" or c.sizeof(PTR) != 8:
            self.reason = "Steam Workshop native integration currently requires Windows x64"
            return False
        try:
            path = runtime_path(self.path)
            if not path.is_file():
                raise OSError(f"Steam runtime not found: {path}")
            self.library = self.loader(str(path), winmode=0x1100)
            self._bind()
            error = c.create_string_buffer(1024)
            if self.library.SteamAPI_InitFlat(error) != 0:
                raise OSError(error.value.decode("utf-8", errors="replace") or "Steam initialization failed")
            self.initialized = True
            self._interfaces()
            self.library.SteamAPI_ManualDispatch_Init()
            self.reason = ""
            return True
        except (OSError, AttributeError, ValueError) as error:
            self.shutdown()
            self.reason = str(error)
            return False

    def _bind(self) -> None:
        for name, (result, arguments) in BASE_FUNCTIONS.items():
            function = getattr(self.library, name)
            function.restype, function.argtypes = result, arguments
        for name, (result, arguments) in UGC_FUNCTIONS.items():
            function = getattr(self.library, "SteamAPI_ISteamUGC_" + name)
            function.restype, function.argtypes = result, [PTR, *arguments]

    def _interfaces(self) -> None:
        self.ugc = self.library.SteamAPI_SteamUGC_v021()
        self.utils = self.library.SteamAPI_SteamUtils_v011()
        self.user = self.library.SteamAPI_SteamUser_v023()
        self.pipe = self.library.SteamAPI_GetHSteamPipe()
        if not all((self.ugc, self.utils, self.user, self.pipe)):
            raise OSError("The Steam client does not provide the required interfaces")
        if self.library.SteamAPI_ISteamUtils_GetAppID(self.utils) != APP_ID:
            raise ValueError("The Steam session belongs to another application")
        self.user_id = self.library.SteamAPI_ISteamUser_GetSteamID(self.user)
        if not self.user_id or not self.library.SteamAPI_ISteamUser_BLoggedOn(self.user):
            raise OSError("Steam must be signed in and online for Workshop")

    def call(self, name: str, *arguments):
        """Call only a bound UGC function in the initialized session."""
        if not self.initialized or name not in UGC_FUNCTIONS:
            raise RuntimeError(self.reason or "Steam function is unavailable")
        return getattr(self.library, "SteamAPI_ISteamUGC_" + name)(self.ugc, *arguments)

    def poll(self, limit: int = 64) -> list[SteamEvent]:
        """Consume a bounded callback batch, releasing each native buffer in finally."""
        if not self.initialized:
            return []
        self.library.SteamAPI_ManualDispatch_RunFrame(self.pipe)
        events = []
        message = CallbackMessage()
        for _ in range(max(1, min(limit, 256))):
            if not self.library.SteamAPI_ManualDispatch_GetNextCallback(self.pipe, c.byref(message)):
                break
            try:
                if not 0 <= message.size <= 1024 * 1024 or (message.size and not message.data):
                    raise ValueError("Invalid native Steam callback size")
                payload = c.string_at(message.data, message.size)
                if message.callback == 703:
                    events.append(self._call_result(payload))
                else:
                    events.append(SteamEvent(message.callback, payload))
            finally:
                self.library.SteamAPI_ManualDispatch_FreeLastCallback(self.pipe)
        return events

    def _call_result(self, payload: bytes) -> SteamEvent:
        if len(payload) != c.sizeof(CallCompleted):
            raise ValueError("Unexpected Steam call-completed layout")
        completed = CallCompleted.from_buffer_copy(payload)
        if not 0 < completed.size <= 1024 * 1024:
            raise ValueError("Invalid Steam call-result size")
        buffer = c.create_string_buffer(completed.size)
        failed = c.c_bool()
        obtained = self.library.SteamAPI_ManualDispatch_GetAPICallResult(
            self.pipe, completed.handle, buffer, completed.size, completed.callback, c.byref(failed))
        return SteamEvent(completed.callback, bytes(buffer), completed.handle,
                          failed.value or not obtained)

    def subscribed_items(self) -> list[dict]:
        """Get installed locations directly from Steam, including nondefault libraries."""
        count = min(self.call("GetNumSubscribedItems", False), 10000)
        ids = (U64 * count)()
        used = min(self.call("GetSubscribedItems", ids, count, False), count)
        items = []
        for item_id in ids[:used]:
            size, timestamp = U64(), U32()
            folder = c.create_string_buffer(32768)
            state = self.call("GetItemState", item_id)
            installed = bool(state & 4) and not bool(state & (16 | 32))
            available = installed and self.call("GetItemInstallInfo", item_id, c.byref(size),
                                               folder, len(folder), c.byref(timestamp))
            items.append({"id": str(item_id), "state": state,
                          "path": folder.value.decode("utf-8") if available else "",
                          "bytes": size.value, "timestamp": timestamp.value})
        return items

    def shutdown(self) -> None:
        """Release successful initialization exactly once."""
        initialized, self.initialized = self.initialized, False
        if initialized and self.library is not None:
            self.library.SteamAPI_Shutdown()
        self.ugc = self.user = self.utils = self.pipe = self.user_id = 0

    def diagnostics(self) -> dict:
        """Read the application's license and preview Cloud quota without account secrets."""
        if not self.initialized:
            return {"available": False, "reason": self.reason}
        storage = self.library.SteamAPI_SteamRemoteStorage_v016()
        apps = self.library.SteamAPI_SteamApps_v009()
        total, available = U64(), U64()
        quota_known = bool(storage and self.library.SteamAPI_ISteamRemoteStorage_GetQuota(
            storage, c.byref(total), c.byref(available)))
        return {"available": True, "app_id": APP_ID,
                "app_license": bool(apps and self.library.SteamAPI_ISteamApps_BIsSubscribedApp(apps, APP_ID)),
                "cloud_quota_known": quota_known, "cloud_total_bytes": total.value,
                "cloud_available_bytes": available.value}
