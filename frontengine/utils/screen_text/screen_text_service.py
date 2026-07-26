"""
讀畫面上的文字：把框選到的一塊畫面交給 Claude，取出文字、翻譯它，或就它問問題。

**這個功能會把螢幕截圖送到 Anthropic 的 API**，是本專案唯一會把畫面內容送出
機器的地方。因此：必須先明確同意（UI 會先問一次並記住）、必須自己提供
ANTHROPIC_API_KEY、而且沒有同意或沒有金鑰時整個功能都是關的。

Read the text on screen: hand a captured region to Claude to pull the text out,
translate it, or answer a question about it.

**This sends a screenshot to Anthropic's API** - the only place in this project
where screen content leaves the machine. So: it needs explicit consent (asked
once and remembered), it needs your own ANTHROPIC_API_KEY, and without either
the whole feature stays off.
"""
from __future__ import annotations

import base64
import os
import threading
from typing import Any, Callable, Dict, List, Optional

from frontengine.utils.logging.loggin_instance import front_engine_logger

API_KEY_ENV = "ANTHROPIC_API_KEY"
MODEL = "claude-opus-5"
MAX_TOKENS = 1500

ACTION_EXTRACT = "extract"
ACTION_TRANSLATE = "translate"
ACTION_ASK = "ask"
ACTIONS = (ACTION_EXTRACT, ACTION_TRANSLATE, ACTION_ASK)

DEFAULT_LANGUAGE = "English"
SYSTEM_PROMPT = (
    "You read a screenshot the user captured and answer about its contents. "
    "Reply with the answer itself and nothing else - no preamble, no commentary "
    "on the image quality, no markdown fences."
)
_PROMPTS = {
    ACTION_EXTRACT: ("Transcribe every piece of text in this image, preserving the reading "
                     "order and line breaks. If there is no text, reply exactly: (no text)"),
    ACTION_TRANSLATE: ("Translate all text in this image into {language}. Keep the layout's "
                       "line breaks. If there is no text, reply exactly: (no text)"),
}


def normalize_action(action: Any) -> str:
    """把動作正規化；不認得的一律當「取出文字」。"""
    name = str(action or "").strip().lower()
    return name if name in ACTIONS else ACTION_EXTRACT


def api_key(env: Optional[dict] = None) -> Optional[str]:
    """從環境變數讀 API 金鑰；沒設定回傳 None（金鑰永遠不寫進設定檔）。"""
    source = env if env is not None else os.environ
    key = str(source.get(API_KEY_ENV, "") or "").strip()
    return key or None


def prompt_for(action: Any, language: str = DEFAULT_LANGUAGE,
               question: str = "") -> str:
    """
    依動作組出要問的話。問問題模式沒填問題時，退回成「取出文字」，
    因為送一張圖卻不問任何事沒有意義。
    The instruction for this action. An "ask" with no question falls back to
    extracting text: sending an image and asking nothing is not useful.
    """
    name = normalize_action(action)
    if name == ACTION_ASK:
        text = str(question or "").strip()
        if text:
            return text
        name = ACTION_EXTRACT
    template = _PROMPTS[name]
    return template.format(language=str(language or DEFAULT_LANGUAGE).strip() or DEFAULT_LANGUAGE)


def image_block(png_bytes: bytes) -> Optional[Dict[str, Any]]:
    """
    把 PNG 位元組包成 API 要的影像內容區塊；沒有資料時回傳 None。
    Wrap PNG bytes as the API's image content block; None when there is nothing.
    """
    if not png_bytes:
        return None
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": "image/png",
            "data": base64.standard_b64encode(png_bytes).decode("ascii"),
        },
    }


def build_message(png_bytes: bytes, action: Any, language: str = DEFAULT_LANGUAGE,
                  question: str = "") -> Optional[List[Dict[str, Any]]]:
    """組出送出去的 messages；沒有影像就回傳 None。"""
    block = image_block(png_bytes)
    if block is None:
        return None
    return [{"role": "user", "content": [block, {"type": "text",
                                                 "text": prompt_for(action, language, question)}]}]


def reply_text(response: Any) -> Optional[str]:
    """
    從回應取出文字。被婉拒（stop_reason 為 refusal）時回傳 None，讓呼叫端
    知道這次沒有答案，而不是把空字串當成結果。
    Pull the text out of a response. A refusal gives None so the caller can tell
    "no answer" from an empty one.
    """
    if response is None:
        return None
    if getattr(response, "stop_reason", None) == "refusal":
        front_engine_logger.info("[ScreenText] request was declined")
        return None
    pieces = []
    for block in getattr(response, "content", None) or []:
        text = getattr(block, "text", None)
        if text:
            pieces.append(str(text))
    joined = "\n".join(pieces).strip()
    return joined or None


class ScreenTextService:
    """
    把截圖交給 Claude 的服務。沒有金鑰、沒有同意或沒有安裝 SDK 時 available()
    為 False，read() 一律回傳 None——不會偷偷送出任何東西。
    The service that hands a screenshot to Claude. Without a key, without
    consent, or without the SDK, available() is False and read() returns None:
    nothing is ever sent quietly.
    """

    def __init__(self, model: str = MODEL,
                 consent_provider: Optional[Callable[[], bool]] = None,
                 key_provider: Optional[Callable[[], Optional[str]]] = None) -> None:
        self.model = model
        self._consent_provider = consent_provider or (lambda: False)
        self._key_provider = key_provider or api_key
        self._client = None

    def consented(self) -> bool:
        """使用者是否已經同意把畫面送出去。"""
        try:
            return bool(self._consent_provider())
        except Exception:  # pragma: no cover - defensive around providers
            return False

    def available(self) -> bool:
        """同意過、有金鑰、也裝得起 SDK 才算可用。"""
        return self.consented() and self._key_provider() is not None

    def _build_client(self):
        if self._client is not None:
            return self._client
        key = self._key_provider()
        if key is None:
            return None
        try:
            from anthropic import Anthropic

            self._client = Anthropic(api_key=key)
        except Exception as error:
            front_engine_logger.warning(f"[ScreenText] client unavailable: {error!r}")
            self._client = None
        return self._client

    def read(self, png_bytes: bytes, action: Any = ACTION_EXTRACT,
             language: str = DEFAULT_LANGUAGE, question: str = "") -> Optional[str]:
        """
        同步送出一次並回傳答案；沒同意、沒金鑰、被婉拒或失敗都回傳 None。
        Ask once, synchronously. None when consent or key is missing, when the
        request is declined, or when it fails.
        """
        if not self.consented():
            front_engine_logger.info("[ScreenText] refused to send: no consent recorded")
            return None
        messages = build_message(png_bytes, action, language, question)
        if messages is None:
            return None
        client = self._build_client()
        if client is None:
            return None
        try:
            response = client.messages.create(
                model=self.model,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                thinking={"type": "disabled"},
                messages=messages,
            )
        except Exception as error:
            front_engine_logger.warning(f"[ScreenText] request failed: {error!r}")
            return None
        return reply_text(response)

    def read_async(self, png_bytes: bytes, on_reply: Callable[[Optional[str]], None],
                   action: Any = ACTION_EXTRACT, language: str = DEFAULT_LANGUAGE,
                   question: str = "") -> None:
        """在背景執行緒送出，完成後以答案呼叫 on_reply（UI 不會被卡住）。"""

        def worker() -> None:
            answer = self.read(png_bytes, action, language, question)
            on_reply(answer)

        threading.Thread(target=worker, name="frontengine-screen-text", daemon=True).start()
