"""
手機遙控：在本機開一個小網頁伺服器，用手機瀏覽器切預設集、隱藏覆蓋層、
翻儀表板頁。

**這會在你的機器上開一個網路埠**，所以預設關閉，而且：
  * 每次啟動都產生一組新權杖，沒有權杖的請求一律拒絕；
  * 只綁定區域網路位址，不對外；
  * 只接受一份寫死的動作清單，網頁端送什麼都不能執行其他東西；
  * 關掉就整個收掉。

A phone remote: a small local web server so a browser on your phone can switch
presets, hide the overlays or page a dashboard.

**This opens a network port on your machine**, so it is off by default, and:
  * a fresh token is minted at every start and required on every request;
  * it binds to the local network address only;
  * it accepts a fixed list of actions - the page cannot ask for anything else;
  * stopping it takes the whole thing down.
"""
from __future__ import annotations

import json
import secrets
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from PySide6.QtCore import QObject, Signal

from frontengine.utils.logging.loggin_instance import front_engine_logger

DEFAULT_PORT = 8770
# 網頁端唯一能要求的動作。名字對應主視窗既有的快速鍵動作，
# 所以遙控做得到的事情，就是使用者本來按快速鍵做得到的事情。
# The only actions the page may ask for. They are the main window's existing
# hotkey actions, so the remote can do exactly what a hotkey can do - no more.
ALLOWED_ACTIONS = ("hide_all", "show_all", "close_all", "mute_all",
                   "opacity_up", "opacity_down", "dashboard_next", "toggle_lock")
_TOKEN_BYTES = 16
_PLAIN_TEXT = "text/plain"
# 用來問「要連外網的話會從哪張網卡出去」。這個位址只拿來讓作業系統挑
# 路由，UDP connect 不會送出任何封包，也不會有人收到什麼。
# Used to ask which interface would be used to reach the outside world. The
# address only makes the OS pick a route: a UDP connect sends no packet, so
# nothing reaches it.
_ROUTE_PROBE = ("8.8.8.8", 80)  # NOSONAR


def make_token() -> str:
    """產生一組一次性的存取權杖。"""
    return secrets.token_urlsafe(_TOKEN_BYTES)


def local_address() -> str:
    """
    本機在區域網路上的位址。問不到就退回 127.0.0.1——那樣只有本機連得上，
    比猜一個錯的位址安全。
    This machine's address on the local network. When it cannot be worked out,
    fall back to 127.0.0.1: only this machine can reach that, which is safer
    than guessing wrong.
    """
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(_ROUTE_PROBE)
        return probe.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        probe.close()


def is_allowed(action: Any) -> bool:
    """這個動作在允許清單裡嗎。"""
    return str(action or "") in ALLOWED_ACTIONS


def token_matches(candidate: Any, expected: str) -> bool:
    """
    常數時間比對權杖。要先轉成 bytes：compare_digest 拿到含非 ASCII 字元的 str
    會丟 TypeError，而權杖是從網路來的——外面隨手送一個 %C3%A9 就能讓處理器
    整個炸掉，連 403 都回不出去。
    Constant-time token comparison, on bytes: compare_digest raises TypeError for
    a str holding non-ASCII characters, and this token arrives over the network -
    a casual %C3%A9 from outside was enough to blow up the handler before it
    could even answer 403.
    """
    return secrets.compare_digest(
        str(candidate or "").encode("utf-8"), str(expected or "").encode("utf-8"))


def parse_request(path: str) -> Tuple[str, Dict[str, str]]:
    """把請求路徑拆成 (路徑, 查詢參數)。"""
    parsed = urlparse(str(path or "/"))
    query = {key: values[0] for key, values in parse_qs(parsed.query).items() if values}
    return (parsed.path or "/", query)


def remote_url(address: str, port: int, token: str) -> str:
    """手機要開的網址（權杖在網址裡，所以掃了 QR 就能用）。"""
    return f"http://{address}:{int(port)}/?token={token}"


PAGE = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>FrontEngine</title><style>
body{font-family:system-ui,sans-serif;margin:0;padding:16px;background:#1b1b1b;color:#eee}
h1{font-size:18px;margin:0 0 16px}
button{width:100%;padding:18px;margin:6px 0;font-size:17px;border:0;border-radius:10px;
background:#2f6f8f;color:#fff}
button:active{background:#1d4a60}
#log{margin-top:14px;font-size:13px;color:#9ab}
</style></head><body><h1>FrontEngine</h1><div id="buttons"></div><div id="log"></div>
<script>
const token=new URLSearchParams(location.search).get("token")||"";
const actions=__ACTIONS__;
const buttons=document.getElementById("buttons"),log=document.getElementById("log");
for(const name of actions){
  const b=document.createElement("button");
  b.textContent=name.replace(/_/g," ");
  b.onclick=async()=>{
    const r=await fetch(`/action?token=${encodeURIComponent(token)}&name=${name}`,{method:"POST"});
    log.textContent=r.ok?`${name} sent`:`${name} refused (${r.status})`;
  };
  buttons.appendChild(b);
}
</script></body></html>"""


class RemoteServer(QObject):
    """
    小型 HTTP 伺服器。請求是在 HTTP 執行緒上處理的，所以動作是以 Qt 訊號送出，
    由呼叫端用 QueuedConnection 接到 UI 執行緒——直接在那條執行緒上碰 Qt
    物件會壞掉，而在那裡開 QTimer 更是完全不會觸發（那條執行緒沒有事件迴圈）。

    A small HTTP server. Requests are handled on the HTTP thread, so actions
    leave as a Qt signal for the caller to take onto the UI thread with a
    QueuedConnection: touching Qt objects from that thread is unsafe, and
    starting a QTimer there simply never fires - it has no event loop.
    """

    action_requested = Signal(str)

    def __init__(self, on_action=None, port: int = DEFAULT_PORT,
                 parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self.port = int(port)
        self.token = make_token()
        self.address = "127.0.0.1"
        self.last_error = ""
        self._on_action = on_action
        self._server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    @property
    def running(self) -> bool:
        return self._server is not None

    def url(self) -> str:
        """目前要在手機上開的網址。"""
        return remote_url(self.address, self.port, self.token)

    def start(self) -> bool:
        """開始服務；埠被佔用等錯誤回傳 False 並記在 last_error。"""
        if self.running:
            return True
        # 每次啟動換一組新權杖，舊的連結就自動失效
        # A new token every start, so an old link stops working by itself.
        self.token = make_token()
        self.address = local_address()
        try:
            self._server = ThreadingHTTPServer((self.address, self.port), self._handler())
        except OSError as error:
            self._server = None
            self.last_error = str(error)
            front_engine_logger.warning(f"[RemoteServer] cannot listen: {error!r}")
            return False
        self._thread = threading.Thread(target=self._server.serve_forever,
                                        name="frontengine-remote", daemon=True)
        self._thread.start()
        front_engine_logger.info(f"[RemoteServer] listening on {self.address}:{self.port}")
        return True

    def stop(self) -> None:
        """停止服務並關閉連線埠。"""
        server, self._server = self._server, None
        if server is None:
            return
        server.shutdown()
        server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
        self._thread = None
        front_engine_logger.info("[RemoteServer] stopped")

    def perform(self, token: str, action: str) -> int:
        """
        處理一個請求，回傳 HTTP 狀態碼。權杖不符是 403，動作不在清單是 400。
        Handle one request and return the status code: 403 for a wrong token,
        400 for an action outside the list.
        """
        if not token_matches(token, self.token):
            front_engine_logger.warning("[RemoteServer] refused a request with a bad token")
            return 403
        if not is_allowed(action):
            return 400
        self.action_requested.emit(str(action))
        if self._on_action is not None:
            self._on_action(str(action))
        return 200

    def _handler(self):
        server = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args) -> None:
                """不要把每個請求都印到 stderr。"""

            def _send(self, status: int, body: bytes, content_type: str) -> None:
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
                path, query = parse_request(self.path)
                if path != "/":
                    self._send(404, b"not found", _PLAIN_TEXT)
                    return
                if not token_matches(query.get("token", ""), server.token):
                    self._send(403, b"bad token", _PLAIN_TEXT)
                    return
                page = PAGE.replace("__ACTIONS__", json.dumps(list(ALLOWED_ACTIONS)))
                self._send(200, page.encode("utf-8"), "text/html; charset=utf-8")

            def do_POST(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
                path, query = parse_request(self.path)
                if path != "/action":
                    self._send(404, b"not found", _PLAIN_TEXT)
                    return
                status = server.perform(query.get("token", ""), query.get("name", ""))
                self._send(status, json.dumps({"status": status}).encode("utf-8"),
                           "application/json")

        return Handler
