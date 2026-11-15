"""Ro'yxat (roster): o'qituvchi faqat ismni kiritadi, o'quvchi ro'yxatdan o'tayotganda "bu menman" deydi."""
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from models.assignment import Submission
from models.attendance import Attendance
from models.grid import GridCell
from models.group import GroupMember
from models.message import ParentMessage
from models.telegram import ParentLink
from models.test import RetakeRequest, TestAttempt
from models.user import ParentContact, User
from services import scoring, storage


def clean_name(raw: str) -> str:
    return " ".join((raw or "").split())[:120]


def purge_placeholder(db: Session, user: User) -> None:
    """Hali ro'yxatdan o'tmagan (claimed=False) o'quvchini va uning barcha ma'lumotini o'chiradi."""
    if user.claimed:
        return
    for s in db.scalars(select(Submission).where(Submission.student_id == user.id)).all():
        storage.delete_file(s.file_path)
        for extra in s.extra_files or []:
            storage.delete_file(extra)
    for model in (GridCell, Attendance, Submission, TestAttempt, RetakeRequest, ParentMessage, GroupMember, ParentLink):
        db.execute(delete(model).where(model.student_id == user.id))
    db.execute(delete(ParentContact).where(ParentContact.student_id == user.id))
    db.delete(user)
    db.flush()


def merge_placeholder(db: Session, ph: User, user: User) -> None:
    """Ro'yxatdagi ism egasi ma'lumotlarini (guruh, baholar, davomat...) haqiqiy hisobga ko'chiradi."""
    for model in (GroupMember, GridCell, Attendance, Submission, TestAttempt, RetakeRequest, ParentMessage, ParentLink):
        db.execute(update(model).where(model.student_id == ph.id).values(student_id=user.id))
    contact = db.scalar(select(ParentContact).where(ParentContact.student_id == ph.id))
    mine = db.scalar(select(ParentContact).where(ParentContact.student_id == user.id))
    if contact and not mine:
        contact.student_id = user.id
    user.name = ph.name  # o'qituvchi kiritgan rasmiy ism
    if not user.track:
        user.track = ph.track
    db.flush()
    db.expire(ph)
    db.execute(delete(ParentContact).where(ParentContact.student_id == ph.id))
    db.delete(ph)
    db.flush()
    scoring.recalculate(db, user.id)
