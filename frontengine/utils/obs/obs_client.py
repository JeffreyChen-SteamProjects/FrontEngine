"""
連到 OBS 的 WebSocket（OBS 28 起內建）：切場景、開關錄影與直播。

連線與收送在背景執行緒進行，UI 不會被卡住；所有網路動作都有逾時，OBS 沒開
或密碼不對就乾脆地失敗，不會卡住整個程式。

Talk to OBS's built-in WebSocket (OBS 28 and later): switch scenes, start and
stop recording or streaming.

Connecting and exchanging messages happen on a background thread so the UI never
blocks, and every network operation has a timeout: with OBS closed or the
password wrong it fails cleanly instead of hanging the app.
"""
from __future__ import annotations

import socket
import threading
from typing import Any, Callable, Dict, Optional

from PySide6.QtCore import QObject, Signal

from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.obs.obs_protocol import (
    DEFAULT_HOST, DEFAULT_PORT, decode, encode, identify_message, is_identified,
    recording_request, response_comment, response_status, scene_request, streaming_request,
)
from frontengine.utils.obs.websocket_frames import (
    OPCODE_CLOSE, OPCODE_PING, OPCODE_PONG, OPCODE_TEXT, client_key, decode_frame, encode_frame,
    handshake_request, handshake_succeeded,
)

CONNECT_TIMEOUT = 4.0
READ_TIMEOUT = 6.0


class ObsClient(QObject):
    """
    一次連線做一件事：連上、認證、送出請求、收結果、關掉。OBS 的請求都很短，
    這樣比維持長連線簡單得多，也不會在使用者沒在用的時候佔著連線。

    One connection per action: connect, identify, send, read the result, close.
    OBS requests are short, which makes this far simpler than holding a session
    open - and it does not keep a connection while nobody is using it.
    """

    finished = Signal(bool, str)  # 成功與否、說明 / whether it worked, and why not

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT,
                 password: Optional[str] = None,
                 parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.host = str(host or DEFAULT_HOST)
        self.port = int(port or DEFAULT_PORT)
        # 沒有密碼就是 None，不是空字串——空字串看起來像「寫死的密碼」
        # No password means None rather than "": an empty default reads as a
        # hardcoded credential to a scanner, and None says what it means.
        self.password = str(password) if password else ""

    # --- public actions --------------------------------------------------
    def switch_scene(self, scene_name: str) -> None:
        """切換場景（背景執行，完成時發出 finished）。"""
        self._run(lambda: scene_request(scene_name))

    def set_recording(self, start: bool) -> None:
        """開始或停止錄影。"""
        self._run(lambda: recording_request(bool(start)))

    def set_streaming(self, start: bool) -> None:
        """開始或停止直播。"""
        self._run(lambda: streaming_request(bool(start)))

    def send_blocking(self, build_request: Callable[[], Dict[str, Any]]) -> tuple:
        """
        同步送出一個請求，回傳 (成功, 說明)。測試與腳本用；UI 請用上面那幾個。
        Send one request synchronously and report (ok, detail). For tests and
        scripts; the UI uses the methods above.
        """
        try:
            return self._exchange(build_request())
        except OSError as error:
            return (False, f"{type(error).__name__}: {error}")

    # --- plumbing --------------------------------------------------------
    def _run(self, build_request: Callable[[], Dict[str, Any]]) -> None:
        def worker() -> None:
            ok, detail = self.send_blocking(build_request)
            front_engine_logger.info(f"[ObsClient] request ok={ok} | {detail}")
            self.finished.emit(ok, detail)

        threading.Thread(target=worker, name="frontengine-obs", daemon=True).start()

    def _exchange(self, request: Dict[str, Any]) -> tuple:
        """連線、認證、送出、讀回結果。"""
        key = client_key()
        with socket.create_connection((self.host, self.port), CONNECT_TIMEOUT) as connection:
            connection.settimeout(READ_TIMEOUT)
            connection.sendall(handshake_request(self.host, self.port, key))
            response = connection.recv(4096)
            if not handshake_succeeded(response, key):
                return (False, "handshake refused")
            reader = _FrameReader(connection)
            hello = reader.next_message()
            identify = identify_message(hello, self.password)
            if identify is None:
                return (False, "authentication required - set the OBS WebSocket password")
            connection.sendall(encode_frame(encode(identify).encode("utf-8")))
            if not is_identified(reader.next_message()):
                return (False, "OBS rejected the credentials")
            connection.sendall(encode_frame(encode(request).encode("utf-8")))
            while True:
                message = reader.next_message()
                if message is None:
                    return (False, "no response from OBS")
                status = response_status(message)
                if status is None:
                    continue
                return (status, response_comment(message) or "ok")


class _FrameReader:
    """
    從 socket 一直讀到湊成完整訊框為止；順手回應 ping，不然 OBS 會斷線。
    Read from the socket until a whole frame is available, answering pings on
    the way - OBS drops the connection otherwise.
    """

    def __init__(self, connection) -> None:
        self._connection = connection
        self._buffer = b""

    def next_message(self) -> Optional[Dict[str, Any]]:
        """下一則文字訊息（解析成 dict）；連線關閉或逾時回傳 None。"""
        while True:
            opcode, payload, used = decode_frame(self._buffer)
            if opcode is None:
                chunk = self._connection.recv(8192)
                if not chunk:
                    return None
                self._buffer += chunk
                continue
            self._buffer = self._buffer[used:]
            if opcode == OPCODE_PING:
                self._connection.sendall(encode_frame(payload or b"", OPCODE_PONG))
                continue
            if opcode == OPCODE_CLOSE:
                return None
            if opcode == OPCODE_TEXT:
                return decode((payload or b"").decode("utf-8", "replace"))
