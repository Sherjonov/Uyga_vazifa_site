from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from deps import (get_db, get_current_user, get_group_for_teacher, require_role,
                  is_member, teacher_has_student)
from messages import AppError
from models.assignment import Assignment, Submission
from models.attendance import Attendance
from models.book import Book, VocabAttempt, VocabUnit
from models.grid import GridCell, GridColumn
from models.group import GroupMember
from models.test import Test, TestAttempt
from models.user import User
from services import scoring
from utils import iso, utcnow

router = APIRouter(prefix="/rating", tags=["rating"])


@router.get("")
def leaderboard(scope: str = "all", group_id: Optional[int] = None, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    """scope=group (group_id kerak) yoki scope=all. Birinchi 3 o'rin alohida, o'z o'rni belgilanadi."""
    if scope == "group":
        if not group_id:
            raise AppError(400, "invalid_value")
        get_group_for_member(db, group_id, user)
        stmt = select(User).join(GroupMember, GroupMember.student_id == User.id).where(GroupMember.group_id == group_id)
    else:
        stmt = select(User).where(User.role == "student", User.claimed.is_(True))
    users = db.scalars(stmt.where(User.is_active.is_(True)).order_by(User.name)).all()

    score_map = scoring.breakdowns(db, [u.id for u in users])
    users = [(u, score_map[u.id]["total"]) for u in users]
    users.sort(key=lambda row: (-row[1], row[0].name.lower()))
    items, me = [], None
    for i, (u, score) in enumerate(users, 1):
        row = {"rank": i, "id": u.id, "name": u.name, "score": score, "is_me": u.id == user.id}
        if row["is_me"]:
            me = row
        items.append(row)
    top = items[:100]
    if me and me["rank"] > 100:
        top.append(me)
    return {"items": top, "me": me, "total": len(items)}


@router.get("/me/breakdown")
def my_breakdown(db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    return scoring.breakdown(db, user.id)


def _score_history(db: Session, student_id: int, group_id: Optional[int] = None) -> dict:
    events = []
    assignment_stmt = (
        select(Submission, Assignment)
        .join(Assignment, Assignment.id == Submission.assignment_id)
        .where(Submission.student_id == student_id, Submission.score.is_not(None))
    )
    test_stmt = (
        select(TestAttempt, Test)
        .join(Test, Test.id == TestAttempt.test_id)
        .where(TestAttempt.student_id == student_id, TestAttempt.status == "finished", TestAttempt.counted.is_(True))
    )
    grid_stmt = select(GridCell, GridColumn).join(GridColumn, GridColumn.id == GridCell.column_id)
    attendance_stmt = select(Attendance).where(Attendance.student_id == student_id)
    if group_id is not None:
        assignment_stmt = assignment_stmt.where(Assignment.group_id == group_id)
        test_stmt = test_stmt.where(Test.group_id == group_id)
        grid_stmt = grid_stmt.where(GridColumn.group_id == group_id, GridCell.student_id == student_id)
        attendance_stmt = attendance_stmt.where(Attendance.group_id == group_id)
    else:
        grid_stmt = grid_stmt.where(GridCell.student_id == student_id)

    for submission, assignment in db.execute(assignment_stmt).all():
        event_at = submission.reviewed_at or submission.submitted_at
        if event_at:
            events.append({
                "id": f"assignment-{submission.id}", "type": assignment.kind, "title": assignment.title,
                "date": iso(event_at), "score": round(float(submission.score), 2), "max_score": assignment.max_score,
                "group_id": assignment.group_id,
            })
        if submission.penalty_points:
            events.append({
                "id": f"resubmit-{submission.id}", "type": "resubmit", "title": assignment.title,
                "date": iso(submission.submitted_at), "score": -round(float(submission.penalty_points), 2),
                "max_score": None, "group_id": assignment.group_id,
            })

    vocab_stmt = (select(VocabAttempt, VocabUnit, Book).join(VocabUnit, VocabUnit.id == VocabAttempt.unit_id)
                  .join(Book, Book.id == VocabUnit.book_id)
                  .where(VocabAttempt.student_id == student_id, VocabAttempt.status == "finished"))
    if group_id is not None:
        vocab_stmt = vocab_stmt.where(Book.group_id == group_id)
    latest_attempts: dict = {}
    for attempt, unit, book in db.execute(vocab_stmt.order_by(VocabAttempt.id)).all():
        latest_attempts[unit.id] = (attempt, unit, book)  # har bir unit uchun oxirgi urinish
    for attempt, unit, book in latest_attempts.values():
        events.append({
            "id": f"vocab-{attempt.id}", "type": "test", "title": f"{book.title} · Unit {unit.unit_number}",
            "date": iso(attempt.finished_at), "score": round(float(attempt.score or 0), 2), "max_score": 10,
            "group_id": book.group_id,
        })

    for a, penalty in scoring.missing_homeworks(db, [student_id], group_id)[student_id]:
        events.append({
            "id": f"missing-{a.id}", "type": "penalty", "title": a.title, "date": iso(a.due_at),
            "score": -round(float(penalty), 2), "max_score": None, "group_id": a.group_id,
        })

    for attempt, test in db.execute(test_stmt).all():
        if attempt.finished_at:
            events.append({
                "id": f"test-{attempt.id}", "type": "test", "title": test.title,
                "date": iso(attempt.finished_at), "score": round(float(attempt.score or 0), 2),
                "max_score": 10, "group_id": test.group_id,
            })

    for cell, column in db.execute(grid_stmt).all():
        try:
            value = float(cell.value.strip().replace(",", "."))
        except (AttributeError, ValueError):
            continue
        if value == value and abs(value) != float("inf"):
            events.append({
                "id": f"grid-{cell.id}", "type": "grid", "title": column.title,
                "date": iso(cell.updated_at), "score": round(value, 2), "max_score": None,
                "group_id": column.group_id,
            })

    for attendance in db.scalars(attendance_stmt).all():
        if attendance.penalty_applied:
            events.append({
                "id": f"attendance-{attendance.id}", "type": "penalty",
                "title": attendance.lesson_title or attendance.date.isoformat(),
                "date": attendance.date.isoformat(), "score": -round(float(attendance.penalty_applied), 2),
                "max_score": None, "group_id": attendance.group_id,
            })

    events.sort(key=lambda event: event["date"] or "", reverse=True)
    summary = {
        "tests": 0.0, "assignments": 0.0, "grid": 0.0,
        "penalties": 0.0, "resubmits": 0.0,
    }
    for event in events:
        if event["type"] == "test":
            summary["tests"] += event["score"]
        elif event["type"] in ("homework", "task"):
            summary["assignments"] += event["score"]
        elif event["type"] == "grid":
            summary["grid"] += event["score"]
        elif event["type"] == "penalty":
            summary["penalties"] -= event["score"]
        elif event["type"] == "resubmit":
            summary["resubmits"] -= event["score"]
    summary["total"] = round(
        summary["tests"] + summary["assignments"] + summary["grid"] - summary["penalties"]
        - summary["resubmits"], 2
    )
    for key in ("tests", "assignments", "grid", "penalties", "resubmits"):
        summary[key] = round(summary[key], 2)
    return {"summary": summary, "items": events}


@router.get("/me/history")
def my_score_history(db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    return _score_history(db, user.id)


@router.get("/students/{student_id}/history")
def student_score_history(student_id: int, group_id: int, db: Session = Depends(get_db),
                          user: User = Depends(require_role("teacher", "admin"))):
    get_group_for_teacher(db, group_id, user)
    if not teacher_has_student(db, user, student_id) or not is_member(db, group_id, student_id):
        raise AppError(404, "not_found")
    return _score_history(db, student_id, group_id)

