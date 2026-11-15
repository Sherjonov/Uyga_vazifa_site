"""Telegram Bot API uchun yupqa mijoz (faqat httpx; qo'shimcha kutubxona kerak emas)."""
import html
import threading
import time
from typing import Any, List, Optional

import httpx

from config import settings

API = "https://api.telegram.org"


class TelegramError(Exception):
    def __init__(self, message: str, code: int = 0):
        super().__init__(message)
        self.code = code

    @property
    def blocked(self) -> bool:
        """Foydalanuvchi botni bloklagan yoki chatni o'chirgan."""
        return self.code in (400, 403) and any(
            w in str(self).lower() for w in ("blocked", "deactivated", "chat not found", "forbidden", "kicked")
        )


def esc(value: Any) -> str:
    """HTML parse_mode uchun xavfsiz matn."""
    return html.escape(str(value if value is not None else ""), quote=False)


def is_configured() -> bool:
    return bool(settings.TELEGRAM_BOT_TOKEN)


_username_cache: dict = {"v": settings.TELEGRAM_BOT_USERNAME or None, "t": 0.0}
_lock = threading.Lock()
_client: Optional[httpx.Client] = None


def _http() -> httpx.Client:
    global _client
    with _lock:
        if _client is None:
            _client = httpx.Client(timeout=httpx.Timeout(35, connect=10))
        return _client


def call(method: str, http_timeout: Optional[float] = None, **params) -> Any:
    """Bot API metodini chaqiradi. Muvaffaqiyatsiz bo'lsa TelegramError."""
    if not settings.TELEGRAM_BOT_TOKEN:
        raise TelegramError("TELEGRAM_BOT_TOKEN is empty")
    url = f"{API}/bot{settings.TELEGRAM_BOT_TOKEN}/{method}"
    try:
        r = _http().post(url, json=params, timeout=http_timeout) if http_timeout else _http().post(url, json=params)
    except httpx.HTTPError as e:
        raise TelegramError(f"network: {e}")
    try:
        data = r.json()
    except ValueError:
        raise TelegramError(f"bad response HTTP {r.status_code}", r.status_code)
    if not data.get("ok"):
        raise TelegramError(str(data.get("description", "error")), int(data.get("error_code") or r.status_code))
    return data.get("result")


def get_me() -> dict:
    me = call("getMe")
    if me.get("username"):
        _username_cache["v"] = me["username"]
    return me


def bot_username() -> Optional[str]:
    if _username_cache["v"] or not is_configured():
        return _username_cache["v"]
    if time.time() - _username_cache["t"] < 60:  # yaqinda urinib ko'rgan: qayta kutib o'tirmaymiz
        return None
    _username_cache["t"] = time.time()
    try:
        return get_me().get("username")
    except TelegramError:
        return None


def bot_url(start: Optional[str] = None) -> Optional[str]:
    name = bot_username()
    if not name:
        return None
    return f"https://t.me/{name}" + (f"?start={start}" if start else "")


def send_message(chat_id: int, text: str, reply_markup: Optional[dict] = None, parse_mode: str = "HTML") -> dict:
    params: dict = {"chat_id": chat_id, "text": text[:4096], "disable_web_page_preview": True}
    if parse_mode:
        params["parse_mode"] = parse_mode
    if reply_markup is not None:
        params["reply_markup"] = reply_markup
    return call("sendMessage", **params)


def edit_message(chat_id: int, message_id: int, text: str, reply_markup: Optional[dict] = None) -> dict:
    params: dict = {"chat_id": chat_id, "message_id": message_id, "text": text[:4096],
                    "parse_mode": "HTML", "disable_web_page_preview": True}
    if reply_markup is not None:
        params["reply_markup"] = reply_markup
    return call("editMessageText", **params)


def answer_callback(callback_id: str, text: str = "", alert: bool = False) -> None:
    try:
        call("answerCallbackQuery", callback_query_id=callback_id, text=text[:200], show_alert=alert)
    except TelegramError:
        pass


def delete_message(chat_id: int, message_id: int) -> None:
    try:
        call("deleteMessage", chat_id=chat_id, message_id=message_id)
    except TelegramError:
        pass


def set_commands(commands: List[dict], chat_id: Optional[int] = None) -> None:
    params: dict = {"commands": commands}
    if chat_id:
        params["scope"] = {"type": "chat", "chat_id": chat_id}
    try:
        call("setMyCommands", **params)
    except TelegramError as e:
        print(f"[telegram] setMyCommands: {e}")


def send_text(chat_id: int, text: str) -> dict:
    """Oddiy xabar yuborish (sayt tomonidan). -> {"ok": bool, "blocked": bool, "error": str|None}"""
    if not is_configured():
        return {"ok": False, "blocked": False, "error": "telegram bot is not configured"}
    try:
        send_message(chat_id, text)
        return {"ok": True, "blocked": False, "error": None}
    except TelegramError as e:
        return {"ok": False, "blocked": e.blocked, "error": str(e)[:300]}
