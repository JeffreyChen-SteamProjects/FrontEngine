"""Extract screen text locally; cloud text or image processing requires explicit consent."""
from __future__ import annotations

import base64
import os
import threading
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from frontengine.utils.logging.loggin_instance import front_engine_logger
from frontengine.utils.screen_text.local_ocr import LocalOcr, OcrBackend, OcrResult

API_KEY_ENV = "ANTHROPIC_API_KEY"
MODEL = "claude-opus-5"
MAX_TOKENS = 1500

ACTION_EXTRACT = "extract"
ACTION_TRANSLATE = "translate"
ACTION_ASK = "ask"
ACTIONS = (ACTION_EXTRACT, ACTION_TRANSLATE, ACTION_ASK)

DEFAULT_LANGUAGE = "English"
SYSTEM_PROMPT = (
    "You read supplied text or a screenshot and answer about its contents. "
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


@dataclass(frozen=True)
class ScreenTextResult:
    status: str
    text: str = ""
    backend: str = ""
    error: str = ""
    consent_required: str = ""


class ScreenTextService:
    """Local-first recognition with separately consented cloud text and image paths."""

    def __init__(self, model: str = MODEL,
                 consent_provider: Optional[Callable[[], bool]] = None,
                 key_provider: Optional[Callable[[], Optional[str]]] = None,
                 local_backend: Optional[OcrBackend] = None,
                 text_consent_provider: Optional[Callable[[], bool]] = None) -> None:
        self.model = model
        self._consent_provider = consent_provider or (lambda: False)
        self._key_provider = key_provider or api_key
        self._client = None
        self.local_backend = local_backend if local_backend is not None else LocalOcr()
        self._text_consent_provider = text_consent_provider or self._consent_provider
        self.last_result = ScreenTextResult("unavailable")

    def consented(self) -> bool:
        """使用者是否已經同意把畫面送出去。"""
        try:
            return bool(self._consent_provider())
        except Exception:  # pragma: no cover - defensive around providers
            return False

    def available(self) -> bool:
        """Local extraction is available independently of cloud credentials or consent."""
        return self.local_backend.available() or self.cloud_available()

    def cloud_available(self) -> bool:
        return self.consented() and self._key_provider() is not None

    def text_consented(self) -> bool:
        try:
            return bool(self._text_consent_provider())
        except Exception:
            return False

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
        """Return extracted/processed text, including empty success; failure returns None."""
        result = self.read_result(png_bytes, action, language, question)
        return result.text if result.status == "success" else None

    def read_result(self, png_bytes: bytes, action: Any = ACTION_EXTRACT,
                    language: str = DEFAULT_LANGUAGE, question: str = "") -> ScreenTextResult:
        result = self._read_result(png_bytes, action, language, question)
        self.last_result = result
        return result

    def _read_result(self, png_bytes: bytes, action: Any, language: str,
                     question: str) -> ScreenTextResult:
        if not png_bytes:
            return ScreenTextResult("error", error="No captured image")
        action = normalize_action(action)
        if action == ACTION_ASK and not str(question or "").strip():
            action = ACTION_EXTRACT
        try:
            local = self.local_backend.recognize(png_bytes)
        except Exception as error:
            local = OcrResult("error", backend=self.local_backend.name, error=str(error))
        if local.successful:
            if not local.text or action == ACTION_EXTRACT:
                return ScreenTextResult("success", local.text, local.backend)
            if not self.text_consented():
                return ScreenTextResult("consent_required", local.text, local.backend,
                                        consent_required="text")
            instruction = prompt_for(action, language, question).replace("in this image", "below")
            messages = [{"role": "user", "content": [
                {"type": "text", "text": "Recognized screen text:\n" + local.text},
                {"type": "text", "text": instruction}]}]
            return self._request(messages, "Anthropic (text via " + local.backend + ")", "text")
        if not self.consented():
            return ScreenTextResult(local.status, backend=local.backend, error=local.error,
                                    consent_required="image")
        messages = build_message(png_bytes, action, language, question)
        return self._request(messages, "Anthropic (screenshot)", "image")

    def _request(self, messages: List[Dict[str, Any]], backend: str,
                 consent_kind: str) -> ScreenTextResult:
        if self._key_provider() is None:
            return ScreenTextResult("unavailable", backend=backend,
                                    error=f"Set {API_KEY_ENV} to use cloud processing")
        client = self._build_client()
        if client is None:
            return ScreenTextResult("unavailable", backend=backend,
                                    error="Anthropic SDK is unavailable")
        consented = self.text_consented() if consent_kind == "text" else self.consented()
        if not consented:
            return ScreenTextResult("consent_required", backend=backend,
                                    consent_required=consent_kind)
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
            return ScreenTextResult("error", backend=backend, error=str(error))
        answer = reply_text(response)
        if answer is None:
            return ScreenTextResult("error", backend=backend, error="No answer was returned")
        return ScreenTextResult("success", answer, backend)

    def read_result_async(self, png_bytes: bytes, on_reply: Callable[[ScreenTextResult], None],
                          action: Any = ACTION_EXTRACT, language: str = DEFAULT_LANGUAGE,
                          question: str = "") -> None:
        def worker() -> None:
            on_reply(self.read_result(png_bytes, action, language, question))

        threading.Thread(target=worker, name="frontengine-screen-text", daemon=True).start()

    def read_async(self, png_bytes: bytes, on_reply: Callable[[Optional[str]], None],
                   action: Any = ACTION_EXTRACT, language: str = DEFAULT_LANGUAGE,
                   question: str = "") -> None:
        """在背景執行緒送出，完成後以答案呼叫 on_reply（UI 不會被卡住）。"""

        def worker() -> None:
            answer = self.read(png_bytes, action, language, question)
            on_reply(answer)

        threading.Thread(target=worker, name="frontengine-screen-text", daemon=True).start()
