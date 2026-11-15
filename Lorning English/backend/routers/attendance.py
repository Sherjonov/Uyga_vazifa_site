from datetime import date as date_type
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from deps import get_db, require_role, get_group_for_teacher, is_member
from messages import AppError
from models.attendance import Attendance
from models.group import Group, GroupMember
from models.user import User
from schemas.attendance import AttendanceIn, AttendanceBulkIn
from services import parent_alerts, scoring
from utils import today

router = APIRouter(prefix="/attendance", tags=["attendance"])


def apply_status(db: Session, group: Group, student_id: int, day: date_type, status: Optional[str], lesson_title=None) -> None:
    """Davomatni belgilaydi va jarimani qayta hisoblaydi (ikki marta ayrilmaydi)."""
    cfg = scoring.get_teacher_settings(db, group.teacher_id)
    penalty_value = {"absent": cfg.absence_penalty, "late": cfg.late_penalty}.get(status or "", 0.0)
    row = db.scalar(select(Attendance).where(
        Attendance.group_id == group.id, Attendance.student_id == student_id, Attendance.date == day))
    if status is None:
        if row:
            db.delete(row)
    else:
        penalty = penalty_value  # absent: -5, late: -3, excused/present: 0
        if row:
            row.status = status
            row.penalty_applied = penalty
            if lesson_title is not None:
                row.lesson_title = lesson_title
        else:
            db.add(Attendance(group_id=group.id, student_id=student_id, date=day, status=status,
                              penalty_applied=penalty, lesson_title=lesson_title))
    db.flush()
    scoring.recalculate(db, student_id)


@router.get("/me")
def my_attendance(db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    rows = db.execute(
        select(Attendance, Group.name).join(Group, Group.id == Attendance.group_id)
        .where(Attendance.student_id == user.id).order_by(Attendance.date.desc()).limit(200)
    ).all()
    totals = {"present": 0, "absent": 0, "excused": 0, "late": 0}
    items = []
    for a, gname in rows:
        totals[a.status] = totals.get(a.status, 0) + 1
        items.append({"date": a.date.isoformat(), "status": a.status, "group": gname,
                      "lesson_title": a.lesson_title, "penalty": a.penalty_applied})
    return {"totals": totals, "items": items}


@router.get("/{group_id}")
def get_attendance(group_id: int, date: Optional[date_type] = None, db: Session = Depends(get_db),
                   user: User = Depends(require_role("teacher"))):
    get_group_for_teacher(db, group_id, user)
    day = date or today()
    students = db.scalars(
        select(User).join(GroupMember, GroupMember.student_id == User.id).where(GroupMember.group_id == group_id).order_by(User.name)
    ).all()
    today_rows = {a.student_id: a for a in db.scalars(select(Attendance).where(Attendance.group_id == group_id, Attendance.date == day)).all()}
    totals: dict = {}
    for sid, st, cnt in db.execute(
        select(Attendance.student_id, Attendance.status, func.count()).where(Attendance.group_id == group_id)
        .group_by(Attendance.student_id, Attendance.status)
    ).all():
        totals.setdefault(sid, {})[st] = cnt
    score_map = scoring.breakdowns(db, [s.id for s in students])
    return {
        "date": day.isoformat(),
        "students": [{
            "id": s.id, "name": s.name,
            "status": today_rows[s.id].status if s.id in today_rows else None,
            "present_total": totals.get(s.id, {}).get("present", 0),
            "absent_total": totals.get(s.id, {}).get("absent", 0),
            "excused_total": totals.get(s.id, {}).get("excused", 0),
            "late_total": totals.get(s.id, {}).get("late", 0),
            "total_score": score_map[s.id]["total"],
        } for s in students],
    }


@router.get("/{group_id}/dates")
def attendance_dates(group_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("teacher"))):
    get_group_for_teacher(db, group_id, user)
    dates = db.scalars(
        select(Attendance.date).where(Attendance.group_id == group_id).distinct().order_by(Attendance.date.desc()).limit(60)
    ).all()
    return [d.isoformat() for d in dates]


@router.put("")
def set_attendance(data: AttendanceIn, db: Session = Depends(get_db), user: User = Depends(require_role("teacher"))):
    group = get_group_for_teacher(db, data.group_id, user)
    if not is_member(db, group.id, data.student_id):
        raise AppError(400, "not_in_group")
    apply_status(db, group, data.student_id, data.date, data.status, data.lesson_title)
    db.commit()
    parent_alerts.notify_attendance_async(group.id, data.student_id, data.date, data.status)  # ota-onaga avtomatik xabar
    student = db.get(User, data.student_id)
    return {"student_id": student.id, "status": data.status, "total_score": scoring.breakdown(db, student.id)["total"]}


@router.put("/bulk")
def set_attendance_bulk(data: AttendanceBulkIn, db: Session = Depends(get_db), user: User = Depends(require_role("teacher"))):
    group = get_group_for_teacher(db, data.group_id, user)
    ids = db.scalars(select(GroupMember.student_id).where(GroupMember.group_id == group.id)).all()
    for sid in ids:
        apply_status(db, group, sid, data.date, data.status)
    db.commit()
    for sid in ids:
        parent_alerts.notify_attendance_async(group.id, sid, data.date, data.status)
    return {"ok": True, "count": len(ids)}
