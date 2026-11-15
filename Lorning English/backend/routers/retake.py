from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from deps import get_db, require_role, get_group_for_teacher, is_member, teacher_group_ids
from messages import AppError
from models.test import Test, TestAttempt, RetakeRequest
from models.user import User
from schemas.test import RetakeIn
from services import scoring
from utils import iso, utcnow

router = APIRouter(prefix="/retake", tags=["retake"])


def _r_out(r: RetakeRequest, test_title: str, student_name: Optional[str] = None) -> dict:
    return {"id": r.id, "test_id": r.test_id, "test_title": test_title, "student_id": r.student_id,
            "student_name": student_name, "reason": r.reason, "status": r.status, "used": r.used,
            "created_at": iso(r.created_at), "resolved_at": iso(r.resolved_at)}


@router.post("")
def create_request(data: RetakeIn, db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    t = db.get(Test, data.test_id)
    if not t or not t.is_published or not is_member(db, t.group_id, user.id):
        raise AppError(403, "test_not_available")
    scoring.expire_stale_attempts(db, t.id, user.id)
    attempts = db.scalars(select(TestAttempt).where(TestAttempt.test_id == t.id, TestAttempt.student_id == user.id)).all()
    if any(a.status == "finished" and a.counted for a in attempts) or any(a.status == "in_progress" for a in attempts) \
            or not any(a.status == "expired" for a in attempts):
        raise AppError(400, "retake_not_needed")
    open_req = db.scalar(select(RetakeRequest).where(
        RetakeRequest.test_id == t.id, RetakeRequest.student_id == user.id,
        RetakeRequest.status.in_(["pending", "approved"]), RetakeRequest.used.is_(False)))
    if open_req:
        raise AppError(409, "retake_pending")
    r = RetakeRequest(test_id=t.id, student_id=user.id, reason=data.reason.strip())
    db.add(r)
    db.commit()
    return _r_out(r, t.title, user.name)


@router.get("/mine")
def my_requests(db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    rows = db.execute(select(RetakeRequest, Test.title).join(Test, Test.id == RetakeRequest.test_id)
                      .where(RetakeRequest.student_id == user.id).order_by(RetakeRequest.id.desc())).all()
    return [_r_out(r, title, user.name) for r, title in rows]


@router.get("")
def list_requests(status: Optional[str] = None, test_id: Optional[int] = None, db: Session = Depends(get_db),
                  user: User = Depends(require_role("teacher"))):
    stmt = (select(RetakeRequest, Test.title, User.name)
            .join(Test, Test.id == RetakeRequest.test_id).join(User, User.id == RetakeRequest.student_id)
            .where(Test.group_id.in_(teacher_group_ids(db, user) or [0])))
    if status in ("pending", "approved", "rejected"):
        stmt = stmt.where(RetakeRequest.status == status)
    if test_id:
        stmt = stmt.where(RetakeRequest.test_id == test_id)
    rows = db.execute(stmt.order_by(RetakeRequest.id.desc())).all()
    return [_r_out(r, title, sname) for r, title, sname in rows]


def _resolve(db: Session, request_id: int, user: User, new_status: str) -> dict:
    r = db.get(RetakeRequest, request_id)
    if not r:
        raise AppError(404, "not_found")
    t = db.get(Test, r.test_id)
    get_group_for_teacher(db, t.group_id, user)
    if r.status != "pending":
        raise AppError(409, "request_resolved")
    r.status = new_status
    r.resolved_at = utcnow()
    db.commit()
    student = db.get(User, r.student_id)
    return _r_out(r, t.title, student.name if student else None)


@router.post("/{request_id}/approve")
def approve(request_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("teacher"))):
    return _resolve(db, request_id, user, "approved")


@router.post("/{request_id}/reject")
def reject(request_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("teacher"))):
    return _resolve(db, request_id, user, "rejected")
