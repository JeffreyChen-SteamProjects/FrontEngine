"""
OBS WebSocket 5.x 的協定計算：認證字串、要送的訊息、回應的解讀。

這裡全部是純函式（只用標準函式庫的 hashlib/base64/json），所以協定本身
可以完整測試，不需要真的開著 OBS。連線的部分在 obs_client。

The protocol maths for OBS WebSocket 5.x: the authentication string, the
messages to send, and how to read the replies.

Everything here is pure (hashlib/base64/json from the standard library), so the
protocol is fully testable without OBS running. The socket lives in obs_client.
"""
from __future__ import annotations

import base64
import hashlib
import json
from typing import Any, Dict, Optional

# OBS WebSocket 5.x 的訊息類型
# The op codes of OBS WebSocket 5.x.
OP_HELLO = 0
OP_IDENTIFY = 1
OP_IDENTIFIED = 2
OP_REQUEST = 6
OP_REQUEST_RESPONSE = 7

RPC_VERSION = 1
DEFAULT_PORT = 4455
DEFAULT_HOST = "127.0.0.1"


def authentication_string(password: str, salt: str, challenge: str) -> str:
    """
    OBS 的認證字串：先把密碼加 salt 取 SHA256 再 base64，接上 challenge，
    再取一次 SHA256 並 base64。這是 OBS 文件寫死的算法。
    OBS's authentication string: base64(sha256(password + salt)), concatenated
    with the challenge, then base64(sha256(...)) again - the algorithm exactly
    as OBS documents it.
    """
    secret = base64.b64encode(
        hashlib.sha256((str(password) + str(salt)).encode("utf-8")).digest()).decode("ascii")
    return base64.b64encode(
        hashlib.sha256((secret + str(challenge)).encode("utf-8")).digest()).decode("ascii")


def hello_needs_auth(hello: Any) -> bool:
    """這個 Hello 有沒有要求認證。"""
    data = hello.get("d") if isinstance(hello, dict) else None
    return isinstance(data, dict) and isinstance(data.get("authentication"), dict)


def identify_message(hello: Any, password: str = "") -> Optional[Dict[str, Any]]:
    """
    依 Hello 組出 Identify 訊息。需要認證卻沒給密碼時回傳 None——
    與其送出一個一定會被拒絕的訊息，不如讓呼叫端知道少了什麼。
    Build the Identify message for this Hello. When authentication is required
    but no password was given, return None: better to tell the caller what is
    missing than to send something certain to be rejected.
    """
    if not isinstance(hello, dict) or hello.get("op") != OP_HELLO:
        return None
    payload: Dict[str, Any] = {"rpcVersion": RPC_VERSION}
    if hello_needs_auth(hello):
        if not str(password or ""):
            return None
        auth = hello["d"]["authentication"]
        payload["authentication"] = authentication_string(
            password, auth.get("salt", ""), auth.get("challenge", ""))
    return {"op": OP_IDENTIFY, "d": payload}


def request_message(request_type: str, request_id: str,
                    request_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """組一個請求訊息（例如切換場景、開始錄影）。"""
    payload: Dict[str, Any] = {
        "requestType": str(request_type),
        "requestId": str(request_id),
    }
    if request_data:
        payload["requestData"] = dict(request_data)
    return {"op": OP_REQUEST, "d": payload}


def scene_request(scene_name: str, request_id: str = "1") -> Dict[str, Any]:
    """切換到某個場景。"""
    return request_message("SetCurrentProgramScene", request_id,
                           {"sceneName": str(scene_name)})


def recording_request(start: bool, request_id: str = "1") -> Dict[str, Any]:
    """開始或停止錄影。"""
    return request_message("StartRecord" if start else "StopRecord", request_id)


def streaming_request(start: bool, request_id: str = "1") -> Dict[str, Any]:
    """開始或停止直播。"""
    return request_message("StartStream" if start else "StopStream", request_id)


def is_identified(message: Any) -> bool:
    """這則訊息是不是「認證完成」。"""
    return isinstance(message, dict) and message.get("op") == OP_IDENTIFIED


def response_status(message: Any) -> Optional[bool]:
    """
    請求的結果：成功 True、失敗 False，不是請求回應則回傳 None。
    The outcome of a request: True, False, or None when it is not a response.
    """
    if not isinstance(message, dict) or message.get("op") != OP_REQUEST_RESPONSE:
        return None
    status = (message.get("d") or {}).get("requestStatus")
    if not isinstance(status, dict):
        return None
    return bool(status.get("result"))


def response_comment(message: Any) -> str:
    """失敗時 OBS 給的說明（沒有就空字串）。"""
    if not isinstance(message, dict):
        return ""
    status = (message.get("d") or {}).get("requestStatus")
    if not isinstance(status, dict):
        return ""
    return str(status.get("comment", "") or "")


def encode(message: Any) -> str:
    """把訊息轉成要送出去的 JSON 文字。"""
    return json.dumps(message, separators=(",", ":"))


def decode(payload: Any) -> Optional[Dict[str, Any]]:
    """把收到的文字解析成訊息；不是 JSON 物件就回傳 None。"""
    try:
        message = json.loads(payload)
    except (TypeError, ValueError):
        return None
    return message if isinstance(message, dict) else None
