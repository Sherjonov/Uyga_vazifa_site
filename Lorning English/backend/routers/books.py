"""Kitoblar: Dars kitobi va Lug'at kitobi (PDF). Lug'at kitobidan unitlar avtomatik ajratiladi."""
from typing import List, Optional

import pymupdf as fitz
from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from deps import (get_db, get_current_user, require_role, get_group_for_teacher, get_group_for_member,
                  student_group_ids, teacher_group_ids)
from messages import AppError
from models.book import Book, VocabUnit
from models.user import User
from routers.vocab import next_lesson_day_passed
from services import ai_service, storage, vocab_service
from services.pdf_service import pdf_to_text
from utils import iso, file_url

router = APIRouter(prefix="/books", tags=["books"])


def b_out(b: Book, units: int = 0, group_name: Optional[str] = None) -> dict:
    return {"id": b.id, "type": b.type, "title": b.title, "group_id": b.group_id, "group_name": group_name,
            "page_count": b.page_count, "pdf_url": file_url(b.file_path), "units_count": units,
            "uploaded_at": iso(b.uploaded_at)}


def _units_out(b: Book, with_words: bool = True, day_passed: bool = False) -> list:
    units = sorted(b.units, key=lambda unit: (unit.unit_number, unit.id))
    return [{
        "id": unit.id,
        "unit_number": unit.unit_number,
        "title": unit.title,
        "words_count": len(unit.words or []),
        "is_default_open": index < 10,
        "open_for_students": index < 10 or unit.teacher_opened or day_passed,
        **({"words": unit.words or []} if with_words else {}),
    } for index, unit in enumerate(units)]


def _book_for_view(db: Session, book_id: int, user: User) -> Book:
    b = db.get(Book, book_id)
    if not b:
        raise AppError(404, "not_found")
    try:
        get_group_for_member(db, b.group_id, user)
    except AppError:
        raise AppError(403, "book_not_available") from None
    return b


def _extract_units(path, kind: str) -> list:
    """Kitob PDF idan faqat Unit larni va ularning lug'atini ajratadi.
    Lug'at kitobida unit topilmasa xato; dars kitobida topilmasa kitob baribir saqlanadi (unitsiz)."""
    strict = kind == "vocab"
    try:
        text = pdf_to_text(path)
    except Exception:
        raise AppError(400, "bad_pdf") from None

    # 1) "Target Words" jadvali (masalan 4000 Essential English Words): faqat shu ro'yxatdagi so'zlar, tarjimasi AI orqali
    toc = vocab_service.parse_target_word_lists(text)
    if toc:
        if not ai_service.is_configured():
            if strict:
                raise AppError(400, "vocab_need_ai")
            return []
        try:
            return vocab_service.translate_units(toc, ai_service.complete)
        except (ai_service.AIError, ValueError) as error:
            print(f"[vocab import] translation failed ({error.__class__.__name__}: {error})")
            if strict:
                raise AppError(502, "vocab_translate_failed") from None
            return []

    # 2) "Unit N" sarlavhalari va "so'z - tarjima" qatorlari
    if kind != "vocab":
        return [u for u in vocab_service.parse_units(text, split_fallback=False) if 2 <= len(u["words"]) <= 500]
    units = vocab_service.parse_units(text)
    if (not units or max((len(unit["words"]) for unit in units), default=0) > 500) and ai_service.is_configured() and len(text.strip()) > 20:
        try:
            extracted = vocab_service.parse_units_with_ai(text, ai_service.complete)
        except (ai_service.AIError, ValueError) as error:
            print(f"[vocab import] AI extraction failed ({error.__class__.__name__}); using text parser result.")
        else:
            if extracted:
                units = extracted
    if any(len(unit["words"]) > 500 for unit in units):
        raise AppError(400, "vocab_parse_failed")
    if not units:
        raise AppError(400, "vocab_no_words")
    return units


@router.post("/{book_id}/reparse")
def reparse_book(book_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("teacher", "admin"))):
    """Kitobdagi unitlarni PDF dan qaytadan ajratadi (noto'g'ri ajralgan bo'lsa). Eski unitlar va ularning natijalari o'chadi."""
    b = db.get(Book, book_id)
    if not b:
        raise AppError(404, "not_found")
    get_group_for_teacher(db, b.group_id, user)
    units = _extract_units(storage.abs_path(b.file_path), b.type)
    for old in list(b.units):
        db.delete(old)
    db.flush()
    for i, u in enumerate(units, 1):
        db.add(VocabUnit(book_id=b.id, unit_number=u["unit_number"] or i, title=u["title"], words=u["words"]))
    db.commit()
    return {"units_count": len(units), "words_count": sum(len(u["words"]) for u in units)}


@router.post("")
def upload_book(
    type: str = Form(..., pattern=r"^(lesson|vocab)$"),
    title: str = Form(..., min_length=1, max_length=200),
    group_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("teacher", "admin")),
):
    get_group_for_teacher(db, group_id, user)
    rel = storage.save_upload(file, "books", {".pdf"}, max_mb=100)
    path = storage.abs_path(rel)
    try:
        doc = fitz.open(str(path))
        pages = doc.page_count
        doc.close()
        if pages == 0:
            raise ValueError("empty")
    except Exception:
        storage.delete_file(rel)
        raise AppError(400, "bad_pdf") from None

    try:
        units = _extract_units(path, type)
    except AppError:
        storage.delete_file(rel)
        raise

    book = Book(type=type, title=title.strip(), file_path=rel, page_count=pages, group_id=group_id, teacher_id=user.id)
    db.add(book)
    db.flush()
    for i, u in enumerate(units, 1):
        db.add(VocabUnit(book_id=book.id, unit_number=u["unit_number"] or i, title=u["title"], words=u["words"]))
    db.commit()
    db.refresh(book)
    return b_out(book, len(units))


@router.get("")
def list_books(type: Optional[str] = None, group_id: Optional[int] = None, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    if group_id:
        get_group_for_member(db, group_id, user)
        gids = [group_id]
    elif user.role == "student":
        gids = student_group_ids(db, user.id)
    else:
        gids = teacher_group_ids(db, user)
    stmt = select(Book).where(Book.group_id.in_(gids or [0]))
    if type in ("lesson", "vocab"):
        stmt = stmt.where(Book.type == type)
    books = db.scalars(stmt.order_by(Book.uploaded_at.desc())).all()
    counts = dict(db.execute(select(VocabUnit.book_id, func.count()).group_by(VocabUnit.book_id)).all())
    from models.group import Group
    names = dict(db.execute(select(Group.id, Group.name)).all())
    return [b_out(b, counts.get(b.id, 0), names.get(b.group_id)) for b in books]


@router.get("/{book_id}")
def get_book(book_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    b = _book_for_view(db, book_id, user)
    return b_out(b, len(b.units))


@router.get("/{book_id}/units")
def book_units(book_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    b = _book_for_view(db, book_id, user)
    return _units_out(b, day_passed=next_lesson_day_passed(db, b))


class UnitEdit(BaseModel):
    title: str = Field(default="", max_length=200)
    words: List[dict] = Field(min_length=1, max_length=500)


class UnitAccess(BaseModel):
    open: bool


@router.put("/{book_id}/units/{unit_id}/access")
def set_unit_access(book_id: int, unit_id: int, data: UnitAccess, db: Session = Depends(get_db),
                    user: User = Depends(require_role("teacher"))):
    book = db.get(Book, book_id)
    unit = db.get(VocabUnit, unit_id)
    if not book or not unit or unit.book_id != book.id:
        raise AppError(404, "not_found")
    get_group_for_teacher(db, book.group_id, user)
    unit.teacher_opened = data.open
    db.commit()
    return {"id": unit.id, "open_for_students": unit.teacher_opened}


@router.put("/{book_id}/units/{unit_id}")
def edit_unit(book_id: int, unit_id: int, data: UnitEdit, db: Session = Depends(get_db),
              user: User = Depends(require_role("teacher", "admin"))):
    """O'qituvchi avtomatik ajratilgan so'zlarni tuzatishi mumkin."""
    b = db.get(Book, book_id)
    u = db.get(VocabUnit, unit_id)
    if not b or not u or u.book_id != b.id:
        raise AppError(404, "not_found")
    get_group_for_teacher(db, b.group_id, user)
    words = []
    for w in data.words:
        en, uz = str(w.get("en", "")).strip()[:80], str(w.get("uz", "")).strip()[:160]
        if en and uz:
            words.append({"en": en, "uz": uz})
    if not words:
        raise AppError(422, "validation_error")
    u.title = data.title.strip()
    u.words = words
    db.commit()
    return {"id": u.id, "unit_number": u.unit_number, "title": u.title, "words_count": len(words), "words": words}


@router.delete("/{book_id}")
def delete_book(book_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("teacher", "admin"))):
    b = db.get(Book, book_id)
    if not b:
        raise AppError(404, "not_found")
    get_group_for_teacher(db, b.group_id, user)
    storage.delete_file(b.file_path)
    db.delete(b)
    db.commit()
    return {"ok": True}
