"""Yon menyudagi hisoblagich (badge) lar: yangi / kutilayotgan ishlar soni."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from deps import get_current_user, get_db, student_group_ids, teacher_group_ids
from models.assignment import Assignment, Submission
from models.book import Book, VocabAttempt, VocabRetake, VocabUnit
from models.message import DirectMessage
from models.test import RetakeRequest, Test, TestAttempt
from models.user import User
from utils import iso, parse_dt, utcnow

router = APIRouter(prefix="/badges", tags=["badges"])
_EPOCH = datetime(2000, 1, 1)


def _count(db: Session, stmt) -> int:
    return int(db.scalar(stmt) or 0)


@router.get("")
def badges(books_since: Optional[str] = None, vocab_since: Optional[str] = None,
           db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Kitoblar va lug'atlar "yangi" hisoblanishi uchun oxirgi ko'rilgan vaqt (books_since / vocab_since) beriladi."""
    out = {"now": iso(utcnow())}
    if user.role == "student":
        gids = student_group_ids(db, user.id) or [0]
        done = select(Submission.assignment_id).where(Submission.student_id == user.id, Submission.submitted_at.is_not(None))
        for kind in ("homework", "extra"):
            out[kind] = _count(db, select(func.count()).select_from(Assignment).where(
                Assignment.group_id.in_(gids), Assignment.kind == kind, Assignment.id.not_in(done)))
        passed = select(TestAttempt.test_id).where(
            TestAttempt.student_id == user.id, TestAttempt.status == "finished", TestAttempt.counted.is_(True))
        out["tests"] = _count(db, select(func.count()).select_from(Test).where(
            Test.group_id.in_(gids), Test.is_published.is_(True), Test.id.not_in(passed)))
        since = parse_dt(books_since) or _EPOCH
        out["books"] = _count(db, select(func.count()).select_from(Book).where(
            Book.group_id.in_(gids), Book.uploaded_at > since))
    elif user.role == "teacher":
        gids = teacher_group_ids(db, user) or [0]
        test_ids = select(Test.id).where(Test.group_id.in_(gids))
        unit_ids = select(VocabUnit.id).join(Book, Book.id == VocabUnit.book_id).where(Book.group_id.in_(gids))
        out["retake"] = _count(db, select(func.count()).select_from(RetakeRequest).where(
            RetakeRequest.status == "pending", RetakeRequest.test_id.in_(test_ids))) \
            + _count(db, select(func.count()).select_from(VocabRetake).where(
                VocabRetake.status == "pending", VocabRetake.unit_id.in_(unit_ids)))
        out["review"] = _count(db, select(func.count()).select_from(Submission).join(
            Assignment, Assignment.id == Submission.assignment_id).where(
            Assignment.group_id.in_(gids), Assignment.kind != "task",
            Submission.submitted_at.is_not(None), Submission.reviewed_at.is_(None)))
        out["messages"] = _count(db, select(func.count()).select_from(DirectMessage).where(
            DirectMessage.recipient_id == user.id, DirectMessage.read_at.is_(None)))
        since = parse_dt(vocab_since) or _EPOCH
        out["vocab"] = _count(db, select(func.count()).select_from(VocabAttempt).where(
            VocabAttempt.unit_id.in_(unit_ids), VocabAttempt.status == "finished", VocabAttempt.finished_at > since))
    return out
