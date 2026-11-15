"""Bitta o'quvchining statistikasi: o'rni, vazifa/topshiriq, test foizi, davomat.
Telegram bot (ota-ona va o'quvchi buyruqlari) shu yerdan foydalanadi."""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from config import settings
from models.assignment import Assignment, Submission
from models.attendance import Attendance
from models.group import Group, GroupMember
from models.test import Test, TestAttempt
from models.user import User
from services import scoring
from utils import utcnow


def local(dt: Optional[datetime]) -> Optional[datetime]:
    """Naive UTC -> mahalliy (APP_TZ_OFFSET) vaqt."""
    return dt + timedelta(hours=settings.APP_TZ_OFFSET) if dt else None


def fmt_dt(dt: Optional[datetime]) -> str:
    d = local(dt)
    return d.strftime("%d.%m %H:%M") if d else "—"


def num(v: float) -> str:
    """5.0 -> '5', 4.5 -> '4.5'"""
    v = round(float(v or 0), 1)
    return str(int(v)) if v == int(v) else str(v)


def group_ids(db: Session, student_id: int) -> List[int]:
    return list(db.scalars(select(GroupMember.group_id).where(GroupMember.student_id == student_id)).all())


def rank_in_group(db: Session, group_id: int, student_id: int) -> Tuple[Optional[int], int]:
    """Reyting sahifasidagi tartib bilan bir xil: ball kamayish bo'yicha, teng bo'lsa ism bo'yicha."""
    users = db.scalars(
        select(User).join(GroupMember, GroupMember.student_id == User.id)
        .where(GroupMember.group_id == group_id, User.is_active.is_(True))
    ).all()
    if not users:
        return None, 0
    scores = scoring.breakdowns(db, [u.id for u in users])
    ordered = sorted(users, key=lambda u: (-scores[u.id]["total"], u.name.lower()))
    for i, u in enumerate(ordered, 1):
        if u.id == student_id:
            return i, len(ordered)
    return None, len(ordered)


def rank_overall(db: Session, student_id: int) -> Optional[Tuple[int, int]]:
    users = db.scalars(select(User).where(User.role == "student", User.claimed.is_(True), User.is_active.is_(True))).all()
    if not any(u.id == student_id for u in users):
        return None
    scores = scoring.breakdowns(db, [u.id for u in users])
    ordered = sorted(users, key=lambda u: (-scores[u.id]["total"], u.name.lower()))
    for i, u in enumerate(ordered, 1):
        if u.id == student_id:
            return i, len(ordered)
    return None


def assignment_block(db: Session, student_id: int, gids: List[int], kind: str) -> dict:
    """kind: homework | task. Holat: graded | checking | missed | pending."""
    now = utcnow()
    items = db.scalars(
        select(Assignment).where(Assignment.group_id.in_(gids or [0]), Assignment.kind == kind)
        .order_by(Assignment.created_at.desc())
    ).all()
    subs = {s.assignment_id: s for s in db.scalars(
        select(Submission).where(Submission.student_id == student_id, Submission.assignment_id.in_([a.id for a in items] or [0]))
    ).all()}
    rows: List[dict] = []
    counts = {"graded": 0, "checking": 0, "missed": 0, "pending": 0}
    points = max_points = 0.0
    for a in items:
        s = subs.get(a.id)
        submitted = bool(s and s.submitted_at)
        if submitted and s.score is not None:
            status = "graded"
            points += float(s.score)
            max_points += float(a.max_score or 0)
        elif submitted:
            status = "checking"
        elif a.due_at and now > a.due_at:
            status = "missed"
        elif kind == "task" and s and s.started_at and a.duration_minutes and now > s.started_at + timedelta(minutes=a.duration_minutes, seconds=5):
            status = "missed"
        else:
            status = "pending"
        counts[status] += 1
        rows.append({
            "id": a.id, "title": a.title, "due_at": a.due_at, "max": float(a.max_score or 0), "status": status,
            "score": float(s.score) if (s and s.score is not None) else None,
            "comment": (s.comment if s else None), "submitted_at": s.submitted_at if s else None,
        })
    done = counts["graded"] + counts["checking"]
    return {"rows": rows, "total": len(rows), "done": done, **counts, "points": round(points, 1), "max_points": round(max_points, 1)}


def tests_block(db: Session, student_id: int, gids: List[int]) -> dict:
    tests = db.scalars(select(Test).where(Test.group_id.in_(gids or [0]), Test.is_published.is_(True)).order_by(Test.created_at.desc())).all()
    attempts = {}
    for a in db.scalars(select(TestAttempt).where(
            TestAttempt.student_id == student_id, TestAttempt.test_id.in_([t.id for t in tests] or [0]),
            TestAttempt.status == "finished", TestAttempt.counted.is_(True))).all():
        attempts[a.test_id] = a
    rows = []
    for t in tests:
        a = attempts.get(t.id)
        rows.append({"id": t.id, "title": t.title, "percent": round(float(a.percent), 1) if a else None,
                     "correct": a.correct_count if a else None, "total": a.total if a else None})
    taken = [r["percent"] for r in rows if r["percent"] is not None]
    return {"rows": rows, "available": len(rows), "taken": len(taken),
            "not_taken": len(rows) - len(taken),
            "avg_percent": round(sum(taken) / len(taken), 1) if taken else None}


def attendance_block(db: Session, student_id: int) -> dict:
    out = {"present": 0, "absent": 0, "excused": 0, "late": 0}
    for st in db.scalars(select(Attendance.status).where(Attendance.student_id == student_id)).all():
        if st in out:
            out[st] += 1
    out["total"] = sum(out.values())
    out["recent_absent"] = [
        {"date": d, "title": t}
        for d, t in db.execute(
            select(Attendance.date, Attendance.lesson_title)
            .where(Attendance.student_id == student_id, Attendance.status == "absent")
            .order_by(Attendance.date.desc()).limit(5)
        ).all()
    ]
    return out


def overview(db: Session, student_id: int) -> Optional[dict]:
    student = db.get(User, student_id)
    if not student or student.role != "student":
        return None
    gids = group_ids(db, student_id)
    groups = []
    for g in db.scalars(select(Group).where(Group.id.in_(gids or [0])).order_by(Group.name)).all():
        rank, total = rank_in_group(db, g.id, student_id)
        teacher = db.get(User, g.teacher_id)
        groups.append({"id": g.id, "name": g.name, "rank": rank, "total": total, "teacher": teacher.name if teacher else None})
    overall = rank_overall(db, student_id)
    return {
        "student": {"id": student.id, "name": student.name, "claimed": bool(student.claimed)},
        "groups": groups,
        "overall": {"rank": overall[0], "total": overall[1]} if overall else None,
        "score": scoring.breakdown(db, student_id),
        "homework": assignment_block(db, student_id, gids, "homework"),
        "tasks": assignment_block(db, student_id, gids, "task"),
        "tests": tests_block(db, student_id, gids),
        "attendance": attendance_block(db, student_id),
    }
