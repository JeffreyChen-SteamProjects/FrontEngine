"""
WebSocket 訊框的編解碼（RFC 6455 中用得到的那一小塊）。

為什麼自己寫：只為了連 OBS 就多一個 WebSocket 套件相依，代價比這段程式碼大。
需要的部分很有限——只送文字訊框、只收文字與控制訊框——而且完全可以測。

WebSocket framing, limited to the part needed here (RFC 6455).

Why hand-rolled: pulling in a WebSocket dependency just to reach OBS costs more
than this code does. The needed surface is small - send text frames, read text
and control frames - and it is entirely testable.
"""
from __future__ import annotations

import base64
import hashlib
import os
import struct
from typing import Optional, Tuple

OPCODE_CONTINUATION = 0x0
OPCODE_TEXT = 0x1
OPCODE_BINARY = 0x2
OPCODE_CLOSE = 0x8
OPCODE_PING = 0x9
OPCODE_PONG = 0xA

_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
_FIN = 0x80
_MASK = 0x80


def client_key() -> str:
    """產生握手用的隨機金鑰（只是防止快取誤判，不是安全機制）。"""
    return base64.b64encode(os.urandom(16)).decode("ascii")


def accept_key(key: str) -> str:
    """
    伺服器該回的 Sec-WebSocket-Accept。RFC 6455 規定就是 SHA-1——它在這裡
    的作用是「證明對方看懂了握手」，不是保護任何機密，換成別的雜湊就不合規格。
    The Sec-WebSocket-Accept the server owes us. RFC 6455 specifies SHA-1;
    its job here is to prove the peer understood the handshake, not to protect
    anything, and any other hash would simply be non-conformant.
    """
    digest = hashlib.sha1(  # nosec B324 # nosemgrep # NOSONAR - RFC 6455 handshake, not a security hash
        (str(key) + _GUID).encode("ascii")).digest()
    return base64.b64encode(digest).decode("ascii")


def handshake_request(host: str, port: int, key: str, path: str = "/") -> bytes:
    """組出升級成 WebSocket 的 HTTP 請求。"""
    lines = [
        f"GET {path} HTTP/1.1",
        f"Host: {host}:{int(port)}",
        "Upgrade: websocket",
        "Connection: Upgrade",
        f"Sec-WebSocket-Key: {key}",
        "Sec-WebSocket-Version: 13",
        "", "",
    ]
    return "\r\n".join(lines).encode("ascii")


def handshake_succeeded(response: bytes, key: str) -> bool:
    """
    檢查伺服器的回應：狀態要是 101，而且 Accept 必須算得出來一樣。
    Check the server's reply: status 101, and an Accept header that matches what
    the key implies.
    """
    try:
        text = response.decode("latin-1")
    except (AttributeError, UnicodeDecodeError):
        return False
    header, _, _rest = text.partition("\r\n\r\n")
    lines = header.split("\r\n")
    if not lines or "101" not in lines[0]:
        return False
    expected = accept_key(key).lower()
    for line in lines[1:]:
        name, _, value = line.partition(":")
        if name.strip().lower() == "sec-websocket-accept":
            return value.strip().lower() == expected
    return False


def encode_frame(payload: bytes, opcode: int = OPCODE_TEXT) -> bytes:
    """
    編一個客戶端訊框。客戶端送出的每一個訊框都必須遮罩（RFC 6455 要求），
    所以這裡一定會加上遮罩鍵。
    Encode a client frame. Every frame a client sends must be masked per RFC
    6455, so a masking key is always applied.
    """
    data = bytes(payload)
    frame = bytearray([_FIN | (opcode & 0x0F)])
    length = len(data)
    if length < 126:
        frame.append(_MASK | length)
    elif length < (1 << 16):
        frame.append(_MASK | 126)
        frame.extend(struct.pack(">H", length))
    else:
        frame.append(_MASK | 127)
        frame.extend(struct.pack(">Q", length))
    mask = os.urandom(4)
    frame.extend(mask)
    frame.extend(byte ^ mask[index % 4] for index, byte in enumerate(data))
    return bytes(frame)


def decode_frame(buffer: bytes) -> Tuple[Optional[int], Optional[bytes], int]:
    """
    從緩衝區解一個訊框，回傳 (opcode, payload, 用掉的位元組數)。
    資料還不夠一個完整訊框時回傳 (None, None, 0)，呼叫端再多讀一點。
    Decode one frame, returning (opcode, payload, bytes consumed). With less
    than a whole frame available it returns (None, None, 0) so the caller can
    read more.
    """
    data = bytes(buffer)
    if len(data) < 2:
        return (None, None, 0)
    opcode = data[0] & 0x0F
    masked = bool(data[1] & _MASK)
    length = data[1] & 0x7F
    index = 2
    if length == 126:
        if len(data) < index + 2:
            return (None, None, 0)
        length = struct.unpack(">H", data[index:index + 2])[0]
        index += 2
    elif length == 127:
        if len(data) < index + 8:
            return (None, None, 0)
        length = struct.unpack(">Q", data[index:index + 8])[0]
        index += 8
    mask = b""
    if masked:
        if len(data) < index + 4:
            return (None, None, 0)
        mask = data[index:index + 4]
        index += 4
    if len(data) < index + length:
        return (None, None, 0)
    payload = data[index:index + length]
    if masked:
        payload = bytes(byte ^ mask[position % 4] for position, byte in enumerate(payload))
    return (opcode, payload, index + length)
