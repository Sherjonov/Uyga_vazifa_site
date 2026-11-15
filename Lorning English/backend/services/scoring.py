"""Ball hisobi bitta joyda: test ballari + vazifa ballari - davomat jarimalari = umumiy reyting."""
import math
from datetime import timedelta
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from models.assignment import Assignment, Submission
from models.group import GroupMember
from models.attendance import Attendance, TeacherSettings
from models.book import VocabAttempt, VocabFinalAttempt
from models.grid import GridCell, GridColumn
from models.test import TestAttempt
from models.user import User
from utils import utcnow

ATTEMPT_GRACE_SECONDS = 20


def get_teacher_settings(db: Session, teacher_id: int) -> TeacherSettings:
    s = db.scalar(select(TeacherSettings).where(TeacherSettings.teacher_id == teacher_id))
    if not s:
        s = TeacherSettings(teacher_id=teacher_id)
        db.add(s)
        db.flush()
    return s


def missing_homeworks(db: Session, student_ids, group_id: Optional[int] = None) -> dict:
    """Muddati o'tgan, lekin topshirilmagan uyga vazifalar: {student_id: [(Assignment, jarima)]}."""
    ids = set(student_ids)
    out: dict = {sid: [] for sid in ids}
    if not ids:
        return out
    stmt = (select(GroupMember.student_id, Assignment).join(Assignment, Assignment.group_id == GroupMember.group_id)
            .where(GroupMember.student_id.in_(ids), Assignment.kind == "homework",
                   Assignment.due_at.is_not(None), Assignment.due_at < utcnow()))
    if group_id is not None:
        stmt = stmt.where(Assignment.group_id == group_id)
    rows = db.execute(stmt).all()
    done = {(sid, aid) for sid, aid in db.execute(
        select(Submission.student_id, Submission.assignment_id)
        .where(Submission.student_id.in_(ids), Submission.submitted_at.is_not(None))).all()}
    per_teacher: dict = {}
    for sid, a in rows:
        if (sid, a.id) in done:
            continue
        if a.teacher_id not in per_teacher:
            per_teacher[a.teacher_id] = float(get_teacher_settings(db, a.teacher_id).hw_missing_penalty or 0)
        if per_teacher[a.teacher_id] > 0:
            out[sid].append((a, per_teacher[a.teacher_id]))
    return out


def breakdowns(db: Session, student_ids) -> dict:
    ids = set(student_ids)
    if not ids:
        return {}
    rows = {
        student_id: {
            "tests": 0.0, "assignments": 0.0, "grid": 0.0, "penalties": 0.0,
            "resubmits": 0.0,
        }
        for student_id in ids
    }

    queries = (
        ("tests", select(TestAttempt.student_id, func.sum(TestAttempt.score))
         .where(TestAttempt.student_id.in_(ids), TestAttempt.status == "finished", TestAttempt.counted.is_(True))
         .group_by(TestAttempt.student_id)),
        ("assignments", select(Submission.student_id, func.sum(Submission.score))
         .where(Submission.student_id.in_(ids), Submission.score.is_not(None)).group_by(Submission.student_id)),
        ("penalties", select(Attendance.student_id, func.sum(Attendance.penalty_applied))
         .where(Attendance.student_id.in_(ids)).group_by(Attendance.student_id)),
        ("resubmits", select(Submission.student_id, func.sum(Submission.penalty_points))
         .where(Submission.student_id.in_(ids)).group_by(Submission.student_id)),
    )
    for key, query in queries:
        for student_id, value in db.execute(query).all():
            rows[student_id][key] = float(value or 0)

    # Lug'at: ball faqat o'tgan urinish uchun beriladi (3 urinishda ham o'ta olmasa ball yo'q); har unit uchun eng yaxshisi
    best_vocab: dict = {}
    for student_id, unit_id, score in db.execute(
        select(VocabAttempt.student_id, VocabAttempt.unit_id, VocabAttempt.score)
        .where(VocabAttempt.student_id.in_(ids), VocabAttempt.status == "finished", VocabAttempt.passed.is_(True))
    ).all():
        key = (student_id, unit_id)
        best_vocab[key] = max(best_vocab.get(key, 0.0), float(score or 0))
    for (student_id, _), score in best_vocab.items():
        rows[student_id]["tests"] += score
    # Yakuniy lug'at testi: o'tgan har bir kitob uchun bir marta (25 ball)
    final_best: dict = {}
    for student_id, book_id, score in db.execute(
        select(VocabFinalAttempt.student_id, VocabFinalAttempt.book_id, VocabFinalAttempt.score)
        .where(VocabFinalAttempt.student_id.in_(ids), VocabFinalAttempt.status == "finished", VocabFinalAttempt.passed.is_(True))
    ).all():
        key = (student_id, book_id)
        final_best[key] = max(final_best.get(key, 0.0), float(score or 0))
    for (student_id, _), score in final_best.items():
        rows[student_id]["tests"] += score

    for student_id, items in missing_homeworks(db, ids).items():
        rows[student_id]["penalties"] += sum(p for _, p in items)  # topshirilmagan vazifa: davomat jarimalari bilan birga

    values = db.execute(
        select(GridCell.student_id, GridCell.value).join(GridColumn, GridColumn.id == GridCell.column_id)
        .where(GridCell.student_id.in_(ids))
    ).all()
    for student_id, value in values:
        try:
            number = float(value.strip().replace(",", "."))
        except (AttributeError, ValueError):
            continue
        if math.isfinite(number):
            rows[student_id]["grid"] += number

    for values in rows.values():
        values["total"] = round(
            values["tests"] + values["assignments"] + values["grid"] - values["penalties"] - values["resubmits"],
            2,
        )
        for key in ("tests", "assignments", "grid", "penalties", "resubmits"):
            values[key] = round(values[key], 2)
    return rows


def breakdown(db: Session, student_id: int) -> dict:
    return breakdowns(db, [student_id])[student_id]


def recalculate(db: Session, student_id: int) -> float:
    user = db.get(User, student_id)
    total = breakdown(db, student_id)["total"]
    if user:
        user.total_score = total
        db.flush()
    return total


def expire_stale_attempts(db: Session, test_id: int, student_id: int, now=None) -> None:
    """Vaqti o'tib ketgan, tugallanmagan urinishlarni 'expired' qiladi."""
    now = now or utcnow()
    rows = db.scalars(
        select(TestAttempt).where(
            TestAttempt.test_id == test_id, TestAttempt.student_id == student_id, TestAttempt.status == "in_progress"
        )
    ).all()
    for a in rows:
        if now > a.deadline_at + timedelta(seconds=ATTEMPT_GRACE_SECONDS):
            a.status = "expired"
    db.flush()
