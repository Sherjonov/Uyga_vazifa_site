import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import settings
from deps import get_db, get_current_user, require_role, get_group_for_teacher, get_group_for_member, student_group_ids, teacher_group_ids
from messages import AppError
from models.lesson import Lesson, LessonSlide
from models.user import User
from services import storage
from services.pdf_service import pdf_to_slides
from services.slide_builder import build_deck
from utils import iso, file_url

router = APIRouter(prefix="/lessons", tags=["lessons"])


def _content_out(content):
    if not content:
        return None
    return {**content, "images": [file_url(p) for p in content.get("images", [])]}


def l_out(l: Lesson, with_slides: bool = False) -> dict:
    d = {"id": l.id, "group_id": l.group_id, "title": l.title, "page_count": l.page_count,
         "pdf_url": file_url(l.pdf_path), "created_at": iso(l.created_at)}
    if with_slides:
        d["slides"] = [{"page": s.page_number, "url": file_url(s.image_path), "content": _content_out(s.content)} for s in l.slides]
    return d


@router.post("")
def create_lesson(
    group_id: int = Form(...),
    title: str = Form(..., min_length=1, max_length=200),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("teacher", "admin")),
):
    get_group_for_teacher(db, group_id, user)
    pdf_rel = storage.save_upload(file, "pdfs", {".pdf"}, max_mb=50)
    slides_key = uuid.uuid4().hex
    out_dir = settings.UPLOAD_DIR / "slides" / slides_key
    try:
        deck = build_deck(storage.abs_path(pdf_rel), out_dir)  # rasm + qurilgan slayd mazmuni
    except Exception:
        try:  # slayd qurib bo'lmasa, oddiy sahifa rasmlari
            deck = [{"image": n, "content": None} for n in pdf_to_slides(storage.abs_path(pdf_rel), out_dir)]
        except Exception:
            storage.delete_file(pdf_rel)
            raise AppError(400, "bad_pdf")
    lesson = Lesson(group_id=group_id, teacher_id=user.id, title=title.strip(), pdf_path=pdf_rel, page_count=len(deck))
    db.add(lesson)
    db.flush()
    for i, d in enumerate(deck, 1):
        content = d["content"]
        if content:
            content["images"] = [f"slides/{slides_key}/{n}" for n in content.get("images", [])]
        db.add(LessonSlide(lesson_id=lesson.id, page_number=i, image_path=f"slides/{slides_key}/{d['image']}", content=content))
    db.commit()
    db.refresh(lesson)
    return l_out(lesson, True)


@router.get("")
def list_lessons(group_id: Optional[int] = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if group_id:
        get_group_for_member(db, group_id, user)
        gids = [group_id]
    elif user.role == "student":
        gids = student_group_ids(db, user.id)
    else:
        gids = teacher_group_ids(db, user)
    rows = db.scalars(select(Lesson).where(Lesson.group_id.in_(gids or [0])).order_by(Lesson.created_at.desc())).all()
    return [l_out(l) for l in rows]


def _get_lesson_for_view(db: Session, lesson_id: int, user: User) -> Lesson:
    l = db.get(Lesson, lesson_id)
    if not l:
        raise AppError(404, "not_found")
    get_group_for_member(db, l.group_id, user)
    return l


@router.get("/{lesson_id}")
def get_lesson(lesson_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return l_out(_get_lesson_for_view(db, lesson_id, user), True)


@router.delete("/{lesson_id}")
def delete_lesson(lesson_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("teacher", "admin"))):
    l = db.get(Lesson, lesson_id)
    if not l:
        raise AppError(404, "not_found")
    get_group_for_teacher(db, l.group_id, user)
    storage.delete_file(l.pdf_path)
    for s in l.slides:
        storage.delete_file(s.image_path)
        for extra in (s.content or {}).get("images", []):
            storage.delete_file(extra)
    db.delete(l)
    db.commit()
    return {"ok": True}
