from typing import Optional

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from deps import get_db, require_role, teacher_has_student, student_group_ids, teacher_group_ids
from messages import AppError, lang_from_request
from models.group import GroupMember
from models.message import ParentMessage
from models.telegram import ParentLink, TelegramAccount
from models.user import User, ParentContact
from schemas.message import ParentContactIn, ParentSendIn
from services import scoring
from services import notifier
from utils import iso, normalize_phone, normalize_email

router = APIRouter(prefix="/parents", tags=["parents"])


def _c_out(c: Optional[ParentContact]) -> dict:
    return {"parent_name": c.parent_name if c else None, "phone": c.phone if c else None, "email": c.email if c else None}


def _save_contact(db: Session, student_id: int, data: ParentContactIn) -> dict:
    phone = normalize_phone(data.phone) if data.phone and data.phone.strip() else None
    email = normalize_email(data.email) if data.email and data.email.strip() else None
    c = db.scalar(select(ParentContact).where(ParentContact.student_id == student_id))
    if not c:
        c = ParentContact(student_id=student_id)
        db.add(c)
    c.parent_name = data.parent_name.strip() if data.parent_name and data.parent_name.strip() else None
    c.phone, c.email = phone, email
    db.commit()
    return _c_out(c)


def _student_for_teacher(db: Session, student_id: int, user: User) -> User:
    student = db.get(User, student_id)
    if not student or student.role != "student":
        raise AppError(404, "not_found")
    if not teacher_has_student(db, user, student_id):
        raise AppError(403, "forbidden")
    return student


# ---- O'quvchining o'z profili ----
@router.get("/me")
def my_contact(db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    return _c_out(db.scalar(select(ParentContact).where(ParentContact.student_id == user.id)))


@router.put("/me")
def update_my_contact(data: ParentContactIn, db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    return _save_contact(db, user.id, data)


# ---- O'qituvchi ----
@router.get("/history")
def history(student_id: Optional[int] = None, db: Session = Depends(get_db), user: User = Depends(require_role("teacher"))):
    stmt = (select(ParentMessage, User.name).join(User, User.id == ParentMessage.student_id)
            .where(ParentMessage.teacher_id == user.id).order_by(ParentMessage.id.desc()).limit(200))
    if student_id:
        stmt = stmt.where(ParentMessage.student_id == student_id)
    return [{"id": m.id, "student_id": m.student_id, "student_name": n, "channel": m.channel, "recipient": m.recipient,
             "body": m.body, "status": m.status, "created_at": iso(m.created_at)} for m, n in db.execute(stmt).all()]


@router.get("/students")
def students_with_contacts(db: Session = Depends(get_db), user: User = Depends(require_role("teacher"))):
    students = db.scalars(select(User).join(GroupMember, GroupMember.student_id == User.id)
                          .where(GroupMember.group_id.in_(teacher_group_ids(db, user) or [0])).distinct().order_by(User.name)).all()
    ids = [s.id for s in students] or [0]
    contacts = {c.student_id: c for c in db.scalars(select(ParentContact).where(ParentContact.student_id.in_(ids))).all()}
    score_map = scoring.breakdowns(db, [s.id for s in students])
    linked: dict = {}
    for link, acc in db.execute(
            select(ParentLink, TelegramAccount).join(TelegramAccount, TelegramAccount.id == ParentLink.telegram_account_id)
            .where(ParentLink.student_id.in_(ids)).order_by(ParentLink.id)).all():
        linked.setdefault(link.student_id, []).append(
            {"link_id": link.id, "name": acc.full_name, "phone": acc.phone, "username": acc.username,
             "blocked": bool(acc.blocked), "linked_at": iso(link.created_at)})
    return [{"id": s.id, "name": s.name, "total_score": score_map[s.id]["total"], "contact": _c_out(contacts.get(s.id)),
             "telegram_parents": linked.get(s.id, []),
             "has_contact": bool(linked.get(s.id) or (contacts.get(s.id) and (contacts[s.id].phone or contacts[s.id].email)))}
            for s in students]


@router.delete("/links/{link_id}")
def unlink_parent(link_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("teacher"))):
    """O'qituvchi ota-onaning botdagi bog'lanishini uzadi (noto'g'ri ulangan bo'lsa)."""
    link = db.get(ParentLink, link_id)
    if not link:
        raise AppError(404, "parent_link_not_found")
    _student_for_teacher(db, link.student_id, user)
    db.delete(link)
    db.commit()
    return {"ok": True}


@router.get("/{student_id}/contact")
def get_contact(student_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("teacher"))):
    _student_for_teacher(db, student_id, user)
    return _c_out(db.scalar(select(ParentContact).where(ParentContact.student_id == student_id)))


@router.put("/{student_id}/contact")
def set_contact(student_id: int, data: ParentContactIn, db: Session = Depends(get_db), user: User = Depends(require_role("teacher"))):
    _student_for_teacher(db, student_id, user)
    return _save_contact(db, student_id, data)


@router.get("/{student_id}/template")
def template(student_id: int, request: Request, db: Session = Depends(get_db), user: User = Depends(require_role("teacher"))):
    student = _student_for_teacher(db, student_id, user)
    gids = student_group_ids(db, student_id)
    return {"body": notifier.build_template(db, student, gids, lang_from_request(request))}


@router.post("/send")
def send(data: ParentSendIn, db: Session = Depends(get_db), user: User = Depends(require_role("teacher"))):
    student = _student_for_teacher(db, data.student_id, user)
    return {"results": notifier.send_to_parent(db, user, student, data.body.strip(), data.channel, data.parent_link_id)}
