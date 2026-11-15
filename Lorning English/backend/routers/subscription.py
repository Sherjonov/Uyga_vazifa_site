from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import settings
from deps import get_db, require_role
from messages import AppError
from models.payment import Payment
from models.user import User
from services import storage, subscription
from utils import file_url, iso, utcnow

router = APIRouter(prefix="/subscription", tags=["subscription"])

RECEIPT_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".pdf"}


def p_out(p: Payment) -> dict:
    return {"id": p.id, "months": p.months, "amount": p.amount, "status": p.status, "admin_note": p.admin_note,
            "is_fraudulent": p.is_fraudulent,
            "receipt_url": file_url(p.receipt_path), "created_at": iso(p.created_at), "reviewed_at": iso(p.reviewed_at),
            "period_start": iso(p.period_start), "period_end": iso(p.period_end)}


@router.get("")
def status(user: User = Depends(require_role("teacher"))):
    return {"subscription": subscription.info(user), "plans": subscription.plans(user.fake_receipt_warning),
            "fake_receipt_warning": user.fake_receipt_warning, "trial_days": settings.TRIAL_DAYS,
            "card": {"number": settings.PAYMENT_CARD_NUMBER, "owner": settings.PAYMENT_CARD_OWNER}}


@router.post("/pay")
def pay(months: int = Form(...), receipt: UploadFile = File(...), db: Session = Depends(get_db),
        user: User = Depends(require_role("teacher"))):
    """Chekni yuborishda obuna faollashadi va chek admin ko'rib chiqishi uchun saqlanadi."""
    standard_price = settings.PLAN_PRICES.get(months)
    if not standard_price:
        raise AppError(400, "invalid_plan")
    if db.scalar(select(Payment.id).where(Payment.teacher_id == user.id, Payment.status == "pending")):
        raise AppError(409, "pending_exists")
    price = 70000 * months if user.fake_receipt_warning else standard_price
    path = storage.save_upload(receipt, "receipts", RECEIPT_EXTS, max_mb=10)
    now = utcnow()
    previous_until = user.subscription_until
    period_start = max(now, previous_until or now)
    period_end = subscription.add_months(period_start, months)
    p = Payment(teacher_id=user.id, months=months, amount=price, receipt_path=path,
                period_start=period_start, period_end=period_end,
                previous_subscription_until=previous_until)
    user.subscription_until = period_end
    user.has_paid = True
    db.add(p)
    db.commit()
    return p_out(p)


@router.get("/payments")
def my_payments(db: Session = Depends(get_db), user: User = Depends(require_role("teacher"))):
    rows = db.scalars(select(Payment).where(Payment.teacher_id == user.id).order_by(Payment.id.desc()).limit(50)).all()
    return [p_out(p) for p in rows]
