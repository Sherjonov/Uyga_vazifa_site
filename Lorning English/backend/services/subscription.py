"""O'qituvchi obunasi: bepul sinov, chek yuborilganda faollashadigan pullik davr."""
import calendar
from datetime import datetime, timedelta
from typing import List, Optional

from config import settings
from utils import iso, utcnow


def plans(fake_receipt_warning: bool = False) -> List[dict]:
    if fake_receipt_warning:
        return [
            {"months": months, "price": 70000 * months, "per_month": 70000, "save": 0}
            for months in sorted(settings.PLAN_PRICES)
        ]
    base = settings.PLAN_PRICES.get(1) or min(settings.PLAN_PRICES.values())
    out = []
    for months in sorted(settings.PLAN_PRICES):
        price = settings.PLAN_PRICES[months]
        out.append({"months": months, "price": price, "per_month": round(price / months), "save": max(0, base * months - price)})
    return out


def add_months(dt: datetime, n: int) -> datetime:
    m = dt.month - 1 + n
    year, month = dt.year + m // 12, m % 12 + 1
    return dt.replace(year=year, month=month, day=min(dt.day, calendar.monthrange(year, month)[1]))


def start_trial(user, now: Optional[datetime] = None) -> None:
    now = now or utcnow()
    user.subscription_until = now + timedelta(days=settings.TRIAL_DAYS)
    user.trial_used = True


def is_active(user, now: Optional[datetime] = None) -> bool:
    if user.role != "teacher":
        return True
    until = user.subscription_until
    return until is None or until > (now or utcnow())


def info(user, now: Optional[datetime] = None) -> dict:
    now = now or utcnow()
    until = user.subscription_until
    left = int((until - now).total_seconds()) if until else None
    return {"active": is_active(user, now), "until": iso(until), "trial": not user.has_paid,
            "seconds_left": max(0, left) if left is not None else None,
            "days_left": max(0, -(-left // 86400)) if left is not None else None}
