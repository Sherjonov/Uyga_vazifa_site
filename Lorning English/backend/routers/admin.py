from datetime import timedelta, datetime, time
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session

from config import settings
from deps import get_db, require_role
from messages import AppError
from models.assignment import Assignment, Submission
from models.group import Group, GroupMember
from models.test import Test, TestAttempt
from models.payment import Payment
from models.ticket import Ticket
from models.user import User
from routers.tickets import t_out
from schemas.auth import user_out
from schemas.payment import PaymentReviewIn
from schemas.ticket import TicketAdminIn
from services import subscription
from services import scoring
from routers.subscription import p_out
from utils import iso, utcnow

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_role("admin"))])


def _month_bounds(k: int):
    """k oy oldingi oyning (mahalliy vaqt bo'yicha) [boshi, keyingi oy boshi) chegarasi, naive UTC da."""
    off = timedelta(hours=settings.APP_TZ_OFFSET)
    local = utcnow() + off
    m = local.month - 1 - k
    year, month = local.year + m // 12, m % 12 + 1
    start = datetime(year, month, 1)
    nxt = datetime(year + (month // 12), month % 12 + 1, 1)
    return start - off, nxt - off, f"{year}-{month:02d}"


def _revenue(db: Session) -> dict:
    """Admin tasdiqlagan to'lovlardan tushgan pul."""
    def total(start=None, end=None):
        stmt = select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.status == "approved")
        if start is not None:
            stmt = stmt.where(Payment.reviewed_at >= start, Payment.reviewed_at < end)
        return int(db.scalar(stmt) or 0)
    months = []
    for k in range(5, -1, -1):
        s, e, label = _month_bounds(k)
        months.append({"month": label, "amount": total(s, e)})
    pending = db.execute(select(func.count(), func.coalesce(func.sum(Payment.amount), 0)).where(Payment.status == "pending")).one()
    return {"this_month": months[-1]["amount"], "last_month": months[-2]["amount"], "total": total(),
            "pending_count": int(pending[0] or 0), "pending_amount": int(pending[1] or 0), "by_month": months}


@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    now = utcnow()
    count = lambda stmt: db.scalar(stmt) or 0  # noqa: E731
    by_role = dict(db.execute(select(User.role, func.count()).where(User.claimed.is_(True)).group_by(User.role)).all())
    by_track = [{"role": r, "track": tr or "none", "count": c} for r, tr, c in
                db.execute(select(User.role, User.track, func.count()).where(User.role != "admin", User.claimed.is_(True)).group_by(User.role, User.track)).all()]
    groups_by_kind = dict(db.execute(select(Group.kind, func.count()).group_by(Group.kind)).all())

    series = []
    for i in range(13, -1, -1):
        day = (now - timedelta(days=i)).date()
        start = datetime.combine(day, time.min)
        end = start + timedelta(days=1)
        series.append({
            "date": day.isoformat(),
            "new_users": count(select(func.count()).select_from(User).where(User.created_at >= start, User.created_at < end)),
            "submissions": count(select(func.count()).select_from(Submission).where(Submission.submitted_at >= start, Submission.submitted_at < end)),
            "test_attempts": count(select(func.count()).select_from(TestAttempt).where(TestAttempt.started_at >= start, TestAttempt.started_at < end)),
            "active_users": count(select(func.count()).select_from(User).where(User.last_seen_at >= start, User.last_seen_at < end)),
        })
    return {
        "revenue": _revenue(db),
        "users": {"total": sum(by_role.values()), "by_role": by_role, "by_track": by_track},
        "groups": {"total": sum(groups_by_kind.values()), "by_kind": groups_by_kind},
        "activity": {
            "daily_active": count(select(func.count()).select_from(User).where(User.last_seen_at >= now - timedelta(days=1))),
            "weekly_active": count(select(func.count()).select_from(User).where(User.last_seen_at >= now - timedelta(days=7))),
        },
        "tests": {"total": count(select(func.count()).select_from(Test)),
                  "finished_attempts": count(select(func.count()).select_from(TestAttempt).where(TestAttempt.status == "finished"))},
        "assignments": {"total": count(select(func.count()).select_from(Assignment)),
                        "submissions": count(select(func.count()).select_from(Submission).where(Submission.submitted_at.is_not(None)))},
        "tickets": {"new": count(select(func.count()).select_from(Ticket).where(Ticket.status == "new"))},
        "series": series,
    }


@router.get("/users")
def list_users(q: Optional[str] = None, role: Optional[str] = None, track: Optional[str] = None,
               page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    stmt = select(User).where(User.claimed.is_(True))
    if q and q.strip():
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(User.name.ilike(like), User.email.ilike(like), User.phone.ilike(like)))
    if role in ("student", "teacher", "admin"):
        stmt = stmt.where(User.role == role)
    if track in ("school", "university", "circle"):
        stmt = stmt.where(User.track == track)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(User.id.desc()).offset((page - 1) * size).limit(size)).all()
    score_map = scoring.breakdowns(db, [u.id for u in rows if u.role == "student"])
    return {"total": total, "page": page, "size": size,
            "items": [{**user_out(u), **({"total_score": score_map[u.id]["total"]} if u.id in score_map else {}),
                       "last_seen_at": iso(u.last_seen_at)} for u in rows]}


@router.put("/users/{user_id}/block")
def block_user(user_id: int, blocked: bool = True, db: Session = Depends(get_db), admin: User = Depends(require_role("admin"))):
    u = db.get(User, user_id)
    if not u:
        raise AppError(404, "not_found")
    if u.id == admin.id:
        raise AppError(400, "cannot_block_self")
    u.is_active = not blocked
    db.commit()
    return user_out(u)


@router.get("/groups")
def list_groups(q: Optional[str] = None, db: Session = Depends(get_db)):
    stmt = select(Group, User.name).join(User, User.id == Group.teacher_id)
    if q and q.strip():
        stmt = stmt.where(Group.name.ilike(f"%{q.strip()}%"))
    counts = dict(db.execute(select(GroupMember.group_id, func.count()).group_by(GroupMember.group_id)).all())
    return [{"id": g.id, "name": g.name, "kind": g.kind, "teacher_id": g.teacher_id, "teacher_name": tn,
             "members_count": counts.get(g.id, 0), "created_at": iso(g.created_at)}
            for g, tn in db.execute(stmt.order_by(Group.id.desc()).limit(300)).all()]


@router.get("/tickets")
def list_tickets(status: Optional[str] = None, db: Session = Depends(get_db)):
    stmt = select(Ticket, User.name, User.role).join(User, User.id == Ticket.author_id)
    if status in ("new", "in_progress", "resolved"):
        stmt = stmt.where(Ticket.status == status)
    rows = db.execute(stmt.order_by(Ticket.id.desc()).limit(300)).all()
    return [{**t_out(t, name), "author_role": role} for t, name, role in rows]


@router.put("/tickets/{ticket_id}")
def update_ticket(ticket_id: int, data: TicketAdminIn, db: Session = Depends(get_db)):
    t = db.get(Ticket, ticket_id)
    if not t:
        raise AppError(404, "not_found")
    if data.status:
        t.status = data.status
    if data.admin_reply is not None and data.admin_reply.strip():
        t.admin_reply = data.admin_reply.strip()
        t.replied_at = utcnow()
        if not data.status and t.status == "new":
            t.status = "in_progress"
    db.commit()
    author = db.get(User, t.author_id)
    return t_out(t, author.name if author else None)


# ---------------- To'lovlar va obunalar ----------------

@router.get("/payments")
def list_payments(status: Optional[str] = None, db: Session = Depends(get_db)):
    stmt = select(Payment, User).join(User, User.id == Payment.teacher_id)
    if status in ("pending", "approved", "rejected"):
        stmt = stmt.where(Payment.status == status)
    rows = db.execute(stmt.order_by(Payment.id.desc()).limit(300)).all()
    return [{**p_out(p), "teacher": {"id": u.id, "name": u.name, "email": u.email, "phone": u.phone},
             "subscription_until": iso(u.subscription_until),
             "fake_receipt_warning": u.fake_receipt_warning} for p, u in rows]


@router.put("/payments/{payment_id}")
def review_payment(payment_id: int, data: PaymentReviewIn, db: Session = Depends(get_db)):
    p = db.get(Payment, payment_id)
    if not p:
        raise AppError(404, "not_found")
    if p.status != "pending":
        raise AppError(409, "payment_resolved")
    now = utcnow()
    teacher = db.get(User, p.teacher_id)
    p.reviewed_at = now
    p.admin_note = (data.note or "").strip() or None
    if data.action == "approve":
        p.status = "approved"
    else:
        p.status = "rejected"
        if p.period_start is not None:
            teacher.subscription_until = p.previous_subscription_until
        if data.action == "fraud":
            p.is_fraudulent = True
            teacher.fake_receipt_warning = True
            p.admin_note = p.admin_note or "Soxta chek yuborilgan"
        teacher.has_paid = db.scalar(
            select(Payment.id).where(Payment.teacher_id == teacher.id, Payment.status == "approved").limit(1)
        ) is not None
    db.commit()
    return {**p_out(p), "subscription_until": iso(teacher.subscription_until)}


@router.get("/subscriptions")
def list_subscriptions(db: Session = Depends(get_db)):
    paid = dict(db.execute(select(Payment.teacher_id, func.coalesce(func.sum(Payment.amount), 0))
                           .where(Payment.status == "approved").group_by(Payment.teacher_id)).all())
    pending = dict(db.execute(select(Payment.teacher_id, func.count()).where(Payment.status == "pending").group_by(Payment.teacher_id)).all())
    teachers = db.scalars(select(User).where(User.role == "teacher").order_by(User.subscription_until.asc())).all()
    now = utcnow()
    return [{"id": u.id, "name": u.name, "email": u.email, "phone": u.phone, **subscription.info(u, now),
             "paid_total": int(paid.get(u.id, 0)), "pending": pending.get(u.id, 0),
             "fake_receipt_warning": u.fake_receipt_warning} for u in teachers]
