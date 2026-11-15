import re
from datetime import datetime, timezone, date
from typing import Optional

from datetime import timedelta

from config import settings
from messages import AppError


def utcnow() -> datetime:
    """Naive UTC (SQLite va PostgreSQL bilan bir xil ishlashi uchun)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def local_day_start_utc(now: Optional[datetime] = None, days: int = 0) -> datetime:
    """Mahalliy (APP_TZ_OFFSET) yarim tundan boshlanadigan vaqtni naive UTC da qaytaradi."""
    now = now or utcnow()
    off = timedelta(hours=settings.APP_TZ_OFFSET)
    start = (now + off).replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=days)
    return start - off


def today() -> date:
    return utcnow().date()


def iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() + "Z" if dt else None


def parse_dt(value: Optional[str]) -> Optional[datetime]:
    """ISO satrni naive UTC datetime ga o'giradi."""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        raise AppError(400, "invalid_date")
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def file_url(path: Optional[str]) -> Optional[str]:
    return f"/uploads/{path}" if path else None


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")


def normalize_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 9:
        digits = "998" + digits
    phone = "+" + digits
    if not re.fullmatch(r"\+998\d{9}", phone):
        raise AppError(400, "invalid_phone")
    return phone


def normalize_email(raw: str) -> str:
    email = (raw or "").strip().lower()
    if not EMAIL_RE.match(email) or len(email) > 255:
        raise AppError(400, "invalid_email")
    return email


def normalize_identifier(raw: str):
    """-> ("email", "a@b.uz") yoki ("phone", "+998901234567")"""
    raw = (raw or "").strip()
    if not raw:
        raise AppError(400, "identifier_required")
    if "@" in raw:
        return "email", normalize_email(raw)
    return "phone", normalize_phone(raw)
