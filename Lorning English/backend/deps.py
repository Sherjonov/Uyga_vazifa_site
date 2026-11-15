from datetime import timedelta
from typing import List

from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import SessionLocal
from messages import AppError
from models.user import User
from models.group import Group, GroupMember
from security import decode_token, role_allowed
from utils import utcnow

bearer = HTTPBearer(auto_error=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(creds: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)) -> User:
    if not creds:
        raise AppError(401, "not_authenticated")
    payload = decode_token(creds.credentials)
    if not payload or payload.get("typ") != "access":
        raise AppError(401, "not_authenticated")
    try:
        user = db.get(User, int(payload["sub"]))
    except (ValueError, KeyError):
        user = None
    if not user:
        raise AppError(401, "not_authenticated")
    if not user.is_active:
        raise AppError(403, "account_blocked")
    if user.role not in ("student", "teacher"):
        raise AppError(403, "forbidden")
    now = utcnow()
    if not user.last_seen_at or now - user.last_seen_at > timedelta(minutes=5):
        user.last_seen_at = now
        db.commit()
    return user


def require_role(*roles: str):
    def dep(user: User = Depends(get_current_user)) -> User:
        if not role_allowed(user, roles):
            raise AppError(403, "forbidden")
        return user
    return dep


# ---------- Guruhlarga kirish huquqi ----------

def is_member(db: Session, group_id: int, student_id: int) -> bool:
    return db.scalar(select(GroupMember.id).where(GroupMember.group_id == group_id, GroupMember.student_id == student_id)) is not None


def student_group_ids(db: Session, student_id: int) -> List[int]:
    return list(db.scalars(select(GroupMember.group_id).where(GroupMember.student_id == student_id)).all())


def teacher_group_ids(db: Session, user: User) -> List[int]:
    return list(db.scalars(select(Group.id).where(Group.teacher_id == user.id)).all())


def get_group_for_teacher(db: Session, group_id: int, user: User) -> Group:
    """Faqat guruh egasi bo'lgan o'qituvchi."""
    g = db.get(Group, group_id)
    if not g:
        raise AppError(404, "group_not_found")
    if user.role == "teacher" and g.teacher_id == user.id:
        return g
    raise AppError(403, "forbidden")


def get_group_for_member(db: Session, group_id: int, user: User) -> Group:
    """Guruh egasi yoki guruh a'zosi."""
    g = db.get(Group, group_id)
    if not g:
        raise AppError(404, "group_not_found")
    if (user.role == "teacher" and g.teacher_id == user.id) or is_member(db, group_id, user.id):
        return g
    raise AppError(403, "forbidden")


def teacher_has_student(db: Session, user: User, student_id: int) -> bool:
    gids = teacher_group_ids(db, user)
    if not gids:
        return False
    return db.scalar(select(GroupMember.id).where(GroupMember.group_id.in_(gids), GroupMember.student_id == student_id)) is not None
