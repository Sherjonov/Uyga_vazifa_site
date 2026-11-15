from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from deps import get_db, require_role, get_group_for_teacher, is_member, teacher_has_student
from messages import AppError
from models.group import Group, GroupMember
from models.user import User
from schemas.auth import user_out
from services import roster as roster_service
from security import hash_password
from utils import iso

router = APIRouter(prefix="/roster", tags=["roster"])


class RosterIn(BaseModel):
    group_id: int
    names: List[str] = Field(min_length=1, max_length=300)


class RenameIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)


class PasswordResetIn(BaseModel):
    password: str = Field(min_length=6, max_length=72)


class ClaimIn(BaseModel):
    student_id: int


# ---------- O'qituvchi: jadvalga faqat ism kiritadi ----------

@router.post("")
def add_names(data: RosterIn, db: Session = Depends(get_db), user: User = Depends(require_role("teacher"))):
    group = get_group_for_teacher(db, data.group_id, user)
    taken = {n.lower() for n in db.scalars(
        select(User.name).join(GroupMember, GroupMember.student_id == User.id).where(GroupMember.group_id == group.id)).all()}
    created, skipped = [], []
    for raw in data.names:
        name = roster_service.clean_name(raw)
        if len(name) < 2 or name.lower() in taken:
            if name:
                skipped.append(name)
            continue
        taken.add(name.lower())
        ph = User(name=name, password_hash="!", role="student", track=group.kind, onboarded=True, claimed=False)
        db.add(ph)
        db.flush()
        db.add(GroupMember(group_id=group.id, student_id=ph.id))
        created.append({"id": ph.id, "name": name})
    db.commit()
    return {"created": created, "skipped": skipped}


@router.put("/{student_id}")
def rename_name(student_id: int, data: RenameIn, db: Session = Depends(get_db),
                user: User = Depends(require_role("teacher"))):
    ph = db.get(User, student_id)
    if not ph or ph.claimed or ph.role != "student":
        raise AppError(404, "not_found")
    if not teacher_has_student(db, user, student_id):
        raise AppError(403, "forbidden")
    name = roster_service.clean_name(data.name)
    if len(name) < 2:
        raise AppError(400, "name_invalid")
    ph.name = name
    db.commit()
    return {"id": ph.id, "name": ph.name}


@router.put("/{student_id}/password")
def reset_student_password(student_id: int, data: PasswordResetIn, db: Session = Depends(get_db),
                           user: User = Depends(require_role("teacher"))):
    student = db.get(User, student_id)
    if not student or student.role != "student" or not student.claimed:
        raise AppError(404, "not_found")
    if not teacher_has_student(db, user, student_id):
        raise AppError(403, "forbidden")
    student.password_hash = hash_password(data.password)
    db.commit()
    return {"ok": True}


# ---------- Ro'yxatdan o'tish sahifasi (login talab qilinmaydi) ----------

@router.get("/public/groups")
def public_groups(db: Session = Depends(get_db)):
    counts = dict(db.execute(
        select(GroupMember.group_id, func.count())
        .join(User, User.id == GroupMember.student_id).where(User.claimed.is_(False)).group_by(GroupMember.group_id)).all())
    # O'qituvchi yaratgan barcha guruhlar (ism kiritilmagan bo'lsa ham) ko'rsatiladi
    rows = db.execute(select(Group, User.name).join(User, User.id == Group.teacher_id).order_by(Group.name)).all()
    return [{"id": g.id, "name": g.name, "kind": g.kind, "teacher_name": tn, "free_count": counts.get(g.id, 0)}
            for g, tn in rows]


@router.get("/public/groups/{group_id}/names")
def public_names(group_id: int, q: Optional[str] = Query(default=None, max_length=60), db: Session = Depends(get_db)):
    stmt = (select(User.id, User.name).join(GroupMember, GroupMember.student_id == User.id)
            .where(GroupMember.group_id == group_id, User.claimed.is_(False)))
    if q and q.strip():
        stmt = stmt.where(User.name.ilike(f"%{q.strip()}%"))
    return [{"id": i, "name": n} for i, n in db.execute(stmt.order_by(User.name).limit(100)).all()]


# ---------- O'quvchi: guruhni tanlab, ismini topadi ----------

@router.get("/groups")
def groups_with_names(db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    """Ism kiritilgan (hali band qilinmagan) o'quvchilari bor guruhlar."""
    counts = dict(db.execute(
        select(GroupMember.group_id, func.count())
        .join(User, User.id == GroupMember.student_id).where(User.claimed.is_(False)).group_by(GroupMember.group_id)).all())
    mine = set(db.scalars(select(GroupMember.group_id).where(GroupMember.student_id == user.id)).all())
    stmt = select(Group, User.name).join(User, User.id == Group.teacher_id).where(Group.id.in_(list(counts) or [0]))
    if user.track:
        stmt = stmt.where(Group.kind == user.track)
    rows = db.execute(stmt.order_by(Group.name)).all()
    return [{"id": g.id, "name": g.name, "kind": g.kind, "teacher_name": tn, "free_count": counts[g.id]}
            for g, tn in rows if g.id not in mine]


@router.get("/groups/{group_id}/names")
def names_in_group(group_id: int, q: Optional[str] = Query(default=None, max_length=60), db: Session = Depends(get_db),
                   user: User = Depends(require_role("student"))):
    if not db.get(Group, group_id):
        raise AppError(404, "group_not_found")
    stmt = (select(User.id, User.name).join(GroupMember, GroupMember.student_id == User.id)
            .where(GroupMember.group_id == group_id, User.claimed.is_(False)))
    if q and q.strip():
        stmt = stmt.where(User.name.ilike(f"%{q.strip()}%"))
    return [{"id": i, "name": n} for i, n in db.execute(stmt.order_by(User.name).limit(100)).all()]


@router.post("/claim")
def claim(data: ClaimIn, db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    ph = db.get(User, data.student_id)
    if not ph or ph.claimed or ph.role != "student" or ph.id == user.id:
        raise AppError(404, "roster_not_found")
    membership = db.scalar(select(GroupMember).where(GroupMember.student_id == ph.id))
    if not membership:
        raise AppError(404, "roster_not_found")
    if is_member(db, membership.group_id, user.id):
        raise AppError(409, "already_member")
    group_id = membership.group_id
    roster_service.merge_placeholder(db, ph, user)
    db.commit()
    group = db.get(Group, group_id)
    return {"user": user_out(user), "group": {"id": group.id, "name": group.name}}
