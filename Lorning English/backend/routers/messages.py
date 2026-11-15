from fastapi import APIRouter, Depends
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import Session

from deps import get_db, get_current_user, teacher_group_ids
from messages import AppError
from models.group import Group, GroupMember
from models.message import DirectMessage
from models.user import User
from schemas.message import DirectIn
from utils import iso, utcnow

router = APIRouter(prefix="/messages", tags=["messages"])


def _related(db: Session, a: User, b: User) -> bool:
    """O'qituvchi va o'quvchi bir guruhda bo'lsagina yozisha oladi."""
    if a.role == "admin" or b.role == "admin":
        return False
    teacher, student = (a, b) if a.role == "teacher" else (b, a)
    if teacher.role != "teacher" or student.role != "student":
        return False
    return db.scalar(select(GroupMember.id).join(Group, Group.id == GroupMember.group_id)
                     .where(Group.teacher_id == teacher.id, GroupMember.student_id == student.id)) is not None


@router.get("/contacts")
def contacts(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.role == "student":
        users = db.scalars(select(User).join(Group, Group.teacher_id == User.id).join(GroupMember, GroupMember.group_id == Group.id)
                           .where(GroupMember.student_id == user.id).distinct().order_by(User.name)).all()
    elif user.role == "teacher":
        users = db.scalars(select(User).join(GroupMember, GroupMember.student_id == User.id)
                           .where(GroupMember.group_id.in_(teacher_group_ids(db, user) or [0]), User.claimed.is_(True)).distinct().order_by(User.name)).all()
    else:
        users = []
    unread = dict(db.execute(select(DirectMessage.sender_id, func.count()).where(
        DirectMessage.recipient_id == user.id, DirectMessage.read_at.is_(None)).group_by(DirectMessage.sender_id)).all())
    return [{"id": u.id, "name": u.name, "role": u.role, "unread": unread.get(u.id, 0)} for u in users]


@router.get("/unread-count")
def unread_count(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    n = db.scalar(select(func.count()).select_from(DirectMessage).where(
        DirectMessage.recipient_id == user.id, DirectMessage.read_at.is_(None)))
    return {"count": n or 0}


@router.get("/thread/{other_id}")
def thread(other_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    other = db.get(User, other_id)
    if not other or not _related(db, user, other):
        raise AppError(403, "message_not_allowed")
    rows = db.scalars(select(DirectMessage).where(or_(
        and_(DirectMessage.sender_id == user.id, DirectMessage.recipient_id == other_id),
        and_(DirectMessage.sender_id == other_id, DirectMessage.recipient_id == user.id)))
        .order_by(DirectMessage.id).limit(500)).all()
    now = utcnow()
    for m in rows:
        if m.recipient_id == user.id and m.read_at is None:
            m.read_at = now
    db.commit()
    return {"user": {"id": other.id, "name": other.name, "role": other.role},
            "messages": [{"id": m.id, "mine": m.sender_id == user.id, "body": m.body, "created_at": iso(m.created_at)} for m in rows]}


@router.post("")
def send_message(data: DirectIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    other = db.get(User, data.recipient_id)
    if not other or not _related(db, user, other):
        raise AppError(403, "message_not_allowed")
    m = DirectMessage(sender_id=user.id, recipient_id=other.id, body=data.body.strip())
    db.add(m)
    db.commit()
    return {"id": m.id, "mine": True, "body": m.body, "created_at": iso(m.created_at)}
