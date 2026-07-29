"""
寵物 AI 對話（可選功能，預設關閉）。使用 Anthropic 官方 SDK 呼叫 Claude；
金鑰只從環境變數 `ANTHROPIC_API_KEY` 讀取，絕不寫進設定檔或程式碼，
未安裝 SDK 或沒有金鑰時整個功能安靜停用。請求在背景執行緒進行，不卡 UI。

Optional AI chat for the pet, off by default. Talks to Claude through the
official Anthropic SDK; the key is read only from the `ANTHROPIC_API_KEY`
environment variable — never written to settings or source — and the feature
disables itself quietly when the SDK or the key is missing. Requests run on a
background thread so the UI never blocks.
"""
from __future__ import annotations

import os
import threading
from typing import Callable, List, Optional

from frontengine.utils.logging.loggin_instance import front_engine_logger

API_KEY_ENV = "ANTHROPIC_API_KEY"
MODEL = "claude-opus-5"
MAX_TOKENS = 300
HISTORY_LIMIT = 10

# 寵物的個性與回話規則；刻意要求極短，因為回覆會顯示在頭上的對話泡泡裡。
# The pet's persona and reply rules. Deliberately terse — the answer is shown
# in a small speech bubble above the pet.
DEFAULT_PERSONA = (
    "You are a small, cheerful desktop pet living on the user's screen. "
    "Reply in at most two short sentences, as the pet would speak. "
    "Match the language the user writes in. "
    "Do not include internal or system XML tags in your response."
)


def api_key(env: Optional[dict] = None) -> Optional[str]:
    """從環境變數取出金鑰；沒設定回傳 None（不讀設定檔，不落地）。"""
    source = os.environ if env is None else env
    key = str(source.get(API_KEY_ENV, "") or "").strip()
    return key or None


def trim_history(history: List[dict], limit: int = HISTORY_LIMIT) -> List[dict]:
    """
    只保留最近的幾輪對話，並確保第一則是使用者發言（API 要求）。
    Keep the most recent turns and make sure the first one is a user message.
    """
    trimmed = [turn for turn in history if isinstance(turn, dict) and turn.get("content")]
    trimmed = trimmed[-max(2, int(limit)):]
    while trimmed and trimmed[0].get("role") != "user":
        trimmed.pop(0)
    return trimmed


def reply_text(response) -> Optional[str]:
    """
    從回應取出文字；被安全機制婉拒（stop_reason 為 refusal）或沒有文字時回傳 None。
    Pull the text out of a response, or None when the request was declined or
    carried no text block.
    """
    if response is None:
        return None
    if getattr(response, "stop_reason", None) == "refusal":
        front_engine_logger.info("[PetChatService] request was declined by safety classifiers")
        return None
    for block in getattr(response, "content", None) or []:
        if getattr(block, "type", None) == "text" and getattr(block, "text", "").strip():
            return block.text.strip()
    return None


class PetChatService:
    """
    把一句話送給 Claude 並取回寵物風格的短回覆。client_factory 可注入以便測試，
    正式路徑會延遲載入 `anthropic` 套件（未安裝時整個功能停用）。
    """

    def __init__(self, persona: str = DEFAULT_PERSONA, model: str = MODEL,
                 client_factory: Optional[Callable[[], object]] = None,
                 key_provider: Callable[[], Optional[str]] = api_key) -> None:
        self.persona = persona
        self.model = model
        self._client_factory = client_factory
        self._key_provider = key_provider
        self._client = None
        self.history: List[dict] = []
        # ask() 會從背景執行緒呼叫，而且可能同時有好幾次在跑
        # ask() runs on background threads, possibly several at once.
        self._ask_lock = threading.Lock()

    def available(self) -> bool:
        """有金鑰（或注入的 client）才算可用 / Usable only with a key or an injected client."""
        if self._client_factory is not None:
            return True
        return self._key_provider() is not None

    def _build_client(self):
        """延遲建立 Anthropic client；套件缺席或建立失敗回傳 None。"""
        if self._client is not None:
            return self._client
        if self._client_factory is not None:
            self._client = self._client_factory()
            return self._client
        key = self._key_provider()
        if not key:
            return None
        try:
            import anthropic

            self._client = anthropic.Anthropic(api_key=key)
        except Exception as error:  # pragma: no cover - optional dependency
            front_engine_logger.warning(f"[PetChatService] anthropic unavailable: {error!r}")
            self._client = None
        return self._client

    def ask(self, message: str) -> Optional[str]:
        """
        同步問一句並回傳寵物的回覆；不可用、被婉拒或發生錯誤時回傳 None。
        Ask synchronously; returns None when unavailable, declined, or failed.
        """
        text = str(message or "").strip()
        if not text:
            return None
        client = self._build_client()
        if client is None:
            return None
        # 兩句話問得夠快就會同時在飛。history 沒有保護的話會排成
        # ['user', 'user']，Messages API 要求角色交替，於是那次請求被拒；更糟的是
        # history 從此變成壞的，之後每一句都失敗，只能等 reset()。
        # Two questions asked in quick succession overlap. Without guarding
        # history they interleave into ['user', 'user'], which the Messages API
        # rejects because roles must alternate - and history stays broken, so
        # every later question fails too until reset().
        with self._ask_lock:
            return self._ask_locked(client, text)

    def _ask_locked(self, client, text: str) -> Optional[str]:
        self.history.append({"role": "user", "content": text})
        self.history = trim_history(self.history)
        # 送出當下的快照：回覆抵達後我們還會再改動 history
        # Send a snapshot — history is appended to again once the reply lands.
        conversation = list(self.history)
        try:
            response = client.messages.create(
                model=self.model,
                max_tokens=MAX_TOKENS,
                system=self.persona,
                # 泡泡只放一兩句話，不需要思考預算；停用思考可讓回覆更快。
                # A one-line bubble needs no thinking budget; disabling it keeps replies snappy.
                thinking={"type": "disabled"},
                output_config={"effort": "low"},
                messages=conversation,
            )
        except Exception as error:
            front_engine_logger.warning(f"[PetChatService] request failed: {error!r}")
            return None
        answer = reply_text(response)
        if answer:
            self.history.append({"role": "assistant", "content": answer})
            self.history = trim_history(self.history)
        return answer

    def ask_async(self, message: str, on_reply: Callable[[Optional[str]], None]) -> None:
        """在背景執行緒問一句，完成後以回覆呼叫 on_reply（UI 不會被卡住）。"""
        def worker() -> None:
            answer = self.ask(message)
            try:
                on_reply(answer)
            except Exception as error:  # pragma: no cover - callback boundary
                front_engine_logger.warning(f"[PetChatService] reply callback failed: {error!r}")

        threading.Thread(target=worker, name="frontengine-pet-chat", daemon=True).start()

    def reset(self) -> None:
        """清掉對話記錄 / Forget the conversation so far."""
        self.history = []
