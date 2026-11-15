"""Telefon raqamga tasdiqlash kodini Telegram bot orqali yetkazish (bot sozlanmagan bo'lsa SMS / DEV konsol)."""
import secrets
from datetime import timedelta
from typing import Optional

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from database import SessionLocal
from models.telegram import TelegramAccount
from models.user import OTPCode
from security import hash_code
from services import telegram_api as tg
from services.sms_service import send_otp_sms
from utils import utcnow


def otp_message(code: str) -> str:
    return (f"🔐 <b>Learning English</b> tasdiqlash kodi:\n\n<code>{tg.esc(code)}</code>\n\n"
            "Kod 10 daqiqa amal qiladi. Uni hech kimga bermang.")


def deliver_phone_otp(phone: str, code: str, lang: str = "uz") -> dict:
    """-> {"ok", "dev", "via", "linked", "bot_url"}.
    Telegram: raqam botga ulangan bo'lsa kod shu zahoti yuboriladi; bo'lmasa foydalanuvchi botni ochib raqamini
    ulashadi va kod o'sha paytda keladi (issue_pending_otp)."""
    if tg.is_configured():
        with SessionLocal() as db:
            acc = db.scalar(select(TelegramAccount).where(TelegramAccount.phone == phone, TelegramAccount.blocked.is_(False)))
            chat_id = acc.chat_id if acc else None
        if chat_id:
            r = tg.send_text(chat_id, otp_message(code))
            if r["ok"]:
                return {"ok": True, "dev": False, "error": None, "via": "telegram", "linked": True, "bot_url": tg.bot_url()}
        return {"ok": True, "dev": False, "error": None, "via": "telegram", "linked": False, "bot_url": tg.bot_url("otp")}
    result = send_otp_sms(phone, code, lang)
    return {**result, "via": "dev" if result.get("dev") else "sms", "linked": False, "bot_url": None}


def issue_pending_otp(db: Session, phone: str) -> Optional[str]:
    """Saytda kod so'ralgan, lekin hali yetkazilmagan bo'lsa: yangi kod yaratib qaytaradi (botda raqam ulangach)."""
    now = utcnow()
    otp = db.scalar(
        select(OTPCode).where(OTPCode.target == phone, OTPCode.purpose == "register", OTPCode.channel == "phone",
                              OTPCode.consumed.is_(False), OTPCode.verified.is_(False), OTPCode.expires_at > now)
        .order_by(desc(OTPCode.created_at)).limit(1))
    if not otp or now - otp.created_at > timedelta(minutes=10):
        return None
    code = f"{secrets.randbelow(10 ** 6):06d}"
    otp.code_hash = hash_code(code)
    otp.attempts = 0
    db.flush()
    return code
