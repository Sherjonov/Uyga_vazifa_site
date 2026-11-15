"""Read-only teacher insights for students who may need support."""
from datetime import timedelta
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from deps import teacher_group_ids
from models.assignment import Assignment, Submission
from models.attendance import Attendance
from models.group import Group, GroupMember
from models.test import Test, TestAttempt
from models.user import User
from services import scoring
from utils import iso, utcnow


def danger_zone(db: Session, teacher: User, group_id: Optional[int] = None) -> list[dict]:
    group_ids = [group_id] if group_id else teacher_group_ids(db, teacher)
    settings = scoring.get_teacher_settings(db, teacher.id)
    now = utcnow()
    since = (now - timedelta(days=14)).date()
    result = []

    groups = db.scalars(
        select(Group).where(Group.id.in_(group_ids or [0])).order_by(Group.name)
    ).all()
    for group in groups:
        students = db.scalars(
            select(User).join(GroupMember, GroupMember.student_id == User.id)
            .where(GroupMember.group_id == group.id, User.is_active.is_(True))
        ).all()
        if not students:
            continue

        student_ids = [student.id for student in students]
        score_map = scoring.breakdowns(db, student_ids)
        due_ids = list(db.scalars(
            select(Assignment.id).where(
                Assignment.group_id == group.id,
                Assignment.kind == "homework",
                Assignment.due_at < now,
            )
        ).all())
        done = {}
        if due_ids:
            done = dict(db.execute(
                select(Submission.student_id, func.count())
                .where(
                    Submission.assignment_id.in_(due_ids),
                    Submission.student_id.in_(student_ids),
                    Submission.submitted_at.is_not(None),
                )
                .group_by(Submission.student_id)
            ).all())

        test_ids = list(db.scalars(
            select(Test.id).where(Test.group_id == group.id, Test.is_published.is_(True))
        ).all())
        avg_tests = {}
        if test_ids:
            avg_tests = dict(db.execute(
                select(TestAttempt.student_id, func.avg(TestAttempt.score))
                .where(
                    TestAttempt.test_id.in_(test_ids),
                    TestAttempt.student_id.in_(student_ids),
                    TestAttempt.status == "finished",
                    TestAttempt.counted.is_(True),
                )
                .group_by(TestAttempt.student_id)
            ).all())

        absences = dict(db.execute(
            select(Attendance.student_id, func.count())
            .where(Attendance.group_id == group.id, Attendance.status == "absent")
            .group_by(Attendance.student_id)
        ).all())
        recent_loss = dict(db.execute(
            select(Attendance.student_id, func.coalesce(func.sum(Attendance.penalty_applied), 0.0))
            .where(Attendance.group_id == group.id, Attendance.date >= since)
            .group_by(Attendance.student_id)
        ).all())

        for student in students:
            reasons = []
            missed = len(due_ids) - int(done.get(student.id, 0))
            if due_ids and missed >= settings.danger_missed_homework:
                reasons.append({
                    "code": "missed_homework",
                    "value": missed,
                    "threshold": settings.danger_missed_homework,
                })
            if student.id in avg_tests and float(avg_tests[student.id]) < settings.danger_low_test_score:
                reasons.append({
                    "code": "low_tests",
                    "value": round(float(avg_tests[student.id]), 2),
                    "threshold": settings.danger_low_test_score,
                })
            if absences.get(student.id, 0) >= settings.danger_absences:
                reasons.append({
                    "code": "absences",
                    "value": absences[student.id],
                    "threshold": settings.danger_absences,
                })
            if float(recent_loss.get(student.id, 0)) >= settings.danger_score_drop:
                reasons.append({
                    "code": "score_drop",
                    "value": round(float(recent_loss[student.id]), 2),
                    "threshold": settings.danger_score_drop,
                })
            if student.claimed and (
                not student.last_seen_at
                or now - student.last_seen_at > timedelta(days=settings.danger_inactive_days)
            ):
                days = (now - student.last_seen_at).days if student.last_seen_at else None
                reasons.append({
                    "code": "inactive",
                    "value": days,
                    "threshold": settings.danger_inactive_days,
                })
            if reasons:
                result.append({
                    "student": {
                        "id": student.id,
                        "name": student.name,
                        "phone": student.phone,
                        "total_score": score_map[student.id]["total"],
                        "last_seen_at": iso(student.last_seen_at),
                    },
                    "group": {"id": group.id, "name": group.name},
                    "reasons": reasons,
                    "level": "high" if len(reasons) >= 3 else ("medium" if len(reasons) == 2 else "low"),
                })

    result.sort(key=lambda row: len(row["reasons"]), reverse=True)
    return result
