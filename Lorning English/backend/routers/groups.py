import re
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session

from deps import get_db, get_current_user, require_role, get_group_for_teacher, student_group_ids
from messages import AppError
from models.attendance import Attendance
from models.group import Group, GroupMember
from models.user import User
from schemas.group import GroupIn, GroupRename, MemberIn
from services import roster as roster_service, scoring
from utils import iso

router = APIRouter(prefix="/groups", tags=["groups"])


def g_out(g: Group, count: int, teacher_name: Optional[str] = None) -> dict:
    return {"id": g.id, "name": g.name, "kind": g.kind, "teacher_id": g.teacher_id,
            "teacher_name": teacher_name, "members_count": count, "created_at": iso(g.created_at)}


@router.post("")
def create_group(data: GroupIn, db: Session = Depends(get_db), user: User = Depends(require_role("teacher"))):
    g = Group(name=data.name.strip(), kind=data.kind, teacher_id=user.id)
    db.add(g)
    db.commit()
    return g_out(g, 0, user.name)


@router.get("")
def list_groups(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = select(Group, User.name).join(User, User.id == Group.teacher_id)
    if user.role == "teacher":
        stmt = stmt.where(Group.teacher_id == user.id)
    elif user.role == "student":
        stmt = stmt.where(Group.id.in_(student_group_ids(db, user.id) or [0]))
    rows = db.execute(stmt.order_by(Group.created_at.desc())).all()
    counts = dict(db.execute(select(GroupMember.group_id, func.count()).group_by(GroupMember.group_id)).all())
    return [g_out(g, counts.get(g.id, 0), tname) for g, tname in rows]


@router.get("/search-students")
def search_students(
    q: str = Query(min_length=2, max_length=60),
    group_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("teacher")),
):
    q = q.strip()
    conds = [User.name.ilike(f"%{q}%"), User.email.ilike(f"%{q}%")]
    digits = re.sub(r"[^\d+]", "", q)
    if len(digits) >= 3:
        conds.append(User.phone.ilike(f"%{digits}%"))
    users = db.scalars(
        select(User).where(User.role == "student", User.is_active.is_(True), User.claimed.is_(True), or_(*conds)).order_by(User.name).limit(20)
    ).all()
    member_ids = set()
    if group_id:
        get_group_for_teacher(db, group_id, user)
        member_ids = set(db.scalars(select(GroupMember.student_id).where(GroupMember.group_id == group_id)).all())
    return [{"id": u.id, "name": u.name, "phone": u.phone, "email": u.email, "track": u.track,
             "is_member": u.id in member_ids} for u in users]


@router.put("/{group_id}")
def rename_group(group_id: int, data: GroupRename, db: Session = Depends(get_db),
                 user: User = Depends(require_role("teacher"))):
    g = get_group_for_teacher(db, group_id, user)
    g.name = data.name.strip()
    db.commit()
    return {"id": g.id, "name": g.name}


@router.delete("/{group_id}")
def delete_group(group_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("teacher"))):
    g = get_group_for_teacher(db, group_id, user)
    ghosts = list(db.scalars(select(User).join(GroupMember, GroupMember.student_id == User.id)
                             .where(GroupMember.group_id == group_id, User.claimed.is_(False))).all())
    db.delete(g)
    db.flush()
    for ghost in ghosts:  # hali ro'yxatdan o'tmagan ismlar ham o'chiriladi
        roster_service.purge_placeholder(db, ghost)
    db.commit()
    return {"ok": True}


@router.get("/{group_id}/members")
def list_members(group_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("teacher"))):
    get_group_for_teacher(db, group_id, user)
    students = db.scalars(
        select(User).join(GroupMember, GroupMember.student_id == User.id)
        .where(GroupMember.group_id == group_id).order_by(User.name)
    ).all()
    absences = dict(db.execute(
        select(Attendance.student_id, func.count())
        .where(Attendance.group_id == group_id, Attendance.status == "absent").group_by(Attendance.student_id)
    ).all())
    score_map = scoring.breakdowns(db, [s.id for s in students])
    return [{"id": s.id, "name": s.name, "phone": s.phone, "email": s.email, "track": s.track, "claimed": s.claimed,
             "total_score": score_map[s.id]["total"], "absences": absences.get(s.id, 0),
             "last_seen_at": iso(s.last_seen_at)} for s in students]


@router.post("/{group_id}/members")
def add_member(group_id: int, data: MemberIn, db: Session = Depends(get_db),
               user: User = Depends(require_role("teacher"))):
    get_group_for_teacher(db, group_id, user)
    student = db.get(User, data.student_id)
    if not student or student.role != "student":
        raise AppError(400, "not_a_student")
    exists = db.scalar(select(GroupMember.id).where(GroupMember.group_id == group_id, GroupMember.student_id == student.id))
    if exists:
        raise AppError(409, "already_member")
    db.add(GroupMember(group_id=group_id, student_id=student.id))
    db.commit()
    return {"ok": True, "student": {"id": student.id, "name": student.name}}


@router.delete("/{group_id}/members/{student_id}")
def remove_member(group_id: int, student_id: int, db: Session = Depends(get_db),
                  user: User = Depends(require_role("teacher"))):
    get_group_for_teacher(db, group_id, user)
    m = db.scalar(select(GroupMember).where(GroupMember.group_id == group_id, GroupMember.student_id == student_id))
    if not m:
        raise AppError(404, "not_in_group")
    student = db.get(User, student_id)
    db.delete(m)
    db.flush()
    if student and not student.claimed:  # ro'yxatga faqat ism kiritilgan bo'lsa, butunlay o'chiriladi
        roster_service.purge_placeholder(db, student)
    db.commit()
    return {"ok": True}
