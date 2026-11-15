"""Lug'at yodlash va himoyalangan imtihon: kamera rasmi, qoidabuzarliklar (ogohlantirish) va avtomatik chiqarish."""
import random
from datetime import timedelta
from typing import Dict, List, Optional, Union

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from deps import get_db, require_role, is_member, get_group_for_teacher, student_group_ids, teacher_group_ids
from config import settings
from messages import AppError
from models.attendance import Attendance
from models.book import Book, VocabUnit, VocabAttempt, VocabRetake, VocabFinalAttempt
from models.group import Group
from models.user import User
from services import scoring, vocab_service
from utils import iso, utcnow

router = APIRouter(prefix="/vocab", tags=["vocab"])

# ---------- yordamchilar ----------

def _unit_book(db: Session, unit_id: int):
    u = db.get(VocabUnit, unit_id)
    b = db.get(Book, u.book_id) if u else None
    if not u or not b:
        raise AppError(404, "not_found")
    return u, b


def _student_unit(db: Session, unit_id: int, user: User):
    u, b = _unit_book(db, unit_id)
    if not is_member(db, b.group_id, user.id):
        raise AppError(403, "book_not_available")
    return u, b


VOCAB_QUESTIONS = 17   # har bir unitdan lug'at savollari
PRACTICE_QUESTIONS = 3  # amaliy savollar (o'zbekcha -> inglizcha)


def _build_questions(words: List[dict]) -> List[dict]:
    """Faqat shu unit so'zlaridan: 17 ta lug'at (so'z -> tarjima variantlari) + 3 ta amaliy savol."""
    words = [w for w in words if w.get("en") and w.get("uz")]
    pool = list(words)
    random.shuffle(pool)
    translations = list(dict.fromkeys(word["uz"] for word in words if word.get("uz")))
    out = []
    for word in pool[:VOCAB_QUESTIONS]:
        options = [word["uz"]]
        distractors = [value for value in translations if value != word["uz"]]
        options.extend(random.sample(distractors, min(3, len(distractors))))
        random.shuffle(options)
        out.append({
            "id": len(out),
            "word": word["en"],
            "uz": word["uz"],
            "type": "choice",
            "options": options,
            "correct_index": options.index(word["uz"]),
        })

    rest = pool[VOCAB_QUESTIONS:]
    practice_words = (random.sample(rest, PRACTICE_QUESTIONS) if len(rest) >= PRACTICE_QUESTIONS
                      else random.sample(pool, min(PRACTICE_QUESTIONS, len(pool))))
    english_words = list(dict.fromkeys(word["en"] for word in words if word.get("en")))
    for word in practice_words:
        options = [word["en"]]
        distractors = [value for value in english_words if value != word["en"]]
        options.extend(random.sample(distractors, min(3, len(distractors))))
        random.shuffle(options)
        out.append({
            "id": len(out),
            "word": word["en"],
            "display_word": word["uz"],
            "uz": word["uz"],
            "type": "choice",
            "practice": True,
            "options": options,
            "correct_index": options.index(word["en"]),
        })
    return out


def _public_questions(questions: List[dict]) -> List[dict]:
    return [{"id": q["id"], "word": q["word"], "type": q["type"],
             **({"display_word": q["display_word"]} if q.get("display_word") else {}),
             **({"practice": True} if q.get("practice") else {}),
             **({"options": q["options"]} if q["type"] == "choice" else {})}
            for q in questions]


def _is_correct(q: dict, value) -> bool:
    if q["type"] == "choice":
        return isinstance(value, int) and not isinstance(value, bool) and value == q.get("correct_index")
    return isinstance(value, str) and vocab_service.normalize_answer(value) in vocab_service.translations(q["uz"])


def _finish(db: Session, a: VocabAttempt, answers: Dict[str, Union[int, str]], pass_percent: int, kicked: bool = False) -> None:
    found, missed = [], []
    for q in a.questions:
        given = answers.get(str(q["id"]))
        item = {
            "en": q["word"],
            "uz": q["uz"],
            "answer": (q["options"][given] if q["type"] == "choice" and isinstance(given, int)
                       and 0 <= given < len(q["options"]) else given),
            "practice": bool(q.get("practice")),
        }
        (found if given is not None and _is_correct(q, given) else missed).append(item)
    total = len(a.questions) or 1
    a.found, a.missed = found, missed
    a.percent = round(len(found) * 100 / total, 1)
    a.kicked_out = kicked
    a.passed = (not kicked) and a.percent >= pass_percent
    a.score = round(a.percent / 10, 2) if a.passed else 0.0  # ball faqat o'tgan urinish uchun
    a.status = "finished"
    a.finished_at = utcnow()
    db.flush()
    scoring.recalculate(db, a.student_id)


def _a_out(a: VocabAttempt, unit: Optional[VocabUnit] = None, book: Optional[Book] = None, student: Optional[User] = None) -> dict:
    d = {"id": a.id, "unit_id": a.unit_id, "student_id": a.student_id, "status": a.status, "passed": a.passed,
         "stopped": bool(a.stopped), "mistakes": a.mistakes or 0,
         "score": a.score, "percent": a.percent, "kicked_out": a.kicked_out, "warnings_count": a.warnings_count,
         "found_count": len(a.found or []), "missed_count": len(a.missed or []), "created_at": iso(a.created_at),
         "finished_at": iso(a.finished_at)}
    if unit:
        d.update({"unit_number": unit.unit_number, "unit_title": unit.title})
    if book:
        d.update({"book_title": book.title, "group_id": book.group_id})
    if student:
        d["student_name"] = student.name
    return d


MAX_UNIT_ATTEMPTS = 3   # har bir unit uchun 3 ta imkoniyat
FREE_UNITS = 10      # boshidagi 10 ta unit hamma uchun ochiq
MAX_MISTAKES = 3     # 3 ta xatodan keyin imtihon avtomatik to'xtaydi


def next_lesson_day_passed(db: Session, book: Book) -> bool:
    """Kitob yuklangan kundan keyin guruhda yana dars (davomat) o'tgan bo'lsa True: qolgan unitlar ochiladi."""
    uploaded_day = (book.uploaded_at + timedelta(hours=settings.APP_TZ_OFFSET)).date()
    return db.scalar(select(Attendance.id).where(Attendance.group_id == book.group_id, Attendance.date > uploaded_day).limit(1)) is not None


def _unit_is_open(db: Session, unit: VocabUnit) -> bool:
    if unit.teacher_opened:
        return True
    book = db.get(Book, unit.book_id)
    if book and next_lesson_day_passed(db, book):
        return True
    preceding_units = db.scalar(
        select(func.count())
        .select_from(VocabUnit)
        .where(
            VocabUnit.book_id == unit.book_id,
            (VocabUnit.unit_number < unit.unit_number)
            | ((VocabUnit.unit_number == unit.unit_number) & (VocabUnit.id < unit.id)),
        )
    )
    return preceding_units < FREE_UNITS


# ---------- O'quvchi ----------

@router.get("/units")
def my_units(db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    gids = student_group_ids(db, user.id)
    rows = db.execute(select(VocabUnit, Book).join(Book, Book.id == VocabUnit.book_id)
                      .where(Book.group_id.in_(gids or [0]))
                      .order_by(Book.id, VocabUnit.unit_number, VocabUnit.id)).all()
    unit_ids = [u.id for u, _ in rows] or [0]
    attempts, attempt_counts, passed_units = {}, {}, set()
    for a in db.scalars(select(VocabAttempt).where(VocabAttempt.student_id == user.id, VocabAttempt.unit_id.in_(unit_ids),
                                                   VocabAttempt.status == "finished").order_by(VocabAttempt.id)).all():
        attempts[a.unit_id] = a
        attempt_counts[a.unit_id] = attempt_counts.get(a.unit_id, 0) + 1
        if a.passed:
            passed_units.add(a.unit_id)
    retakes = {}
    for r in db.scalars(select(VocabRetake).where(VocabRetake.student_id == user.id, VocabRetake.unit_id.in_(unit_ids))
                        .order_by(VocabRetake.id)).all():
        retakes[r.unit_id] = r
    out = []
    unit_order: Dict[int, int] = {}
    day_passed: Dict[int, bool] = {}
    for u, b in rows:
        position = unit_order.get(b.id, 0)
        unit_order[b.id] = position + 1
        if b.id not in day_passed:
            day_passed[b.id] = next_lesson_day_passed(db, b)
        open_for_students = position < FREE_UNITS or u.teacher_opened or day_passed[b.id]
        a, r = attempts.get(u.id), retakes.get(u.id)
        used = attempt_counts.get(u.id, 0)
        # O'tolmagan (lekin chiqarilmagan) o'quvchi 3 martagacha o'zi topshiradi; boshqa holatda o'qituvchi ruxsati kerak
        self_ok = bool(a and not a.passed and not a.kicked_out and used < MAX_UNIT_ATTEMPTS)
        retake_ok = bool(r and r.status == "approved" and not r.used) or self_ok
        out.append({
            "id": u.id, "book_id": b.id, "book_title": b.title, "unit_number": u.unit_number, "title": u.title,
            "words_count": len(u.words or []),
            "open_for_students": open_for_students,
            "passed": u.id in passed_units,
            "attempts_used": used,
            "attempts_left": 0 if u.id in passed_units else max(0, MAX_UNIT_ATTEMPTS - used),
            "attempt": ({"passed": a.passed, "score": a.score, "percent": a.percent, "kicked_out": a.kicked_out,
                         "warnings_count": a.warnings_count, "found_count": len(a.found or []), "missed_count": len(a.missed or []),
                         "missed": a.missed or [], "created_at": iso(a.finished_at)} if a else None),
            "retake": ({"id": r.id, "status": r.status, "used": r.used, "teacher_note": r.teacher_note} if r else None),
            "can_start": open_for_students and ((a is None) or retake_ok),
        })
    return out


@router.get("/units/{unit_id}/words")
def unit_words(unit_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    u, b = _student_unit(db, unit_id, user)
    return {"id": u.id, "unit_number": u.unit_number, "title": u.title, "book_title": b.title, "words": u.words or []}


@router.post("/units/{unit_id}/start")
def start_exam(unit_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    u, b = _student_unit(db, unit_id, user)
    if not _unit_is_open(db, u):
        raise AppError(403, "vocab_unit_locked")
    cfg = scoring.get_teacher_settings(db, b.teacher_id)
    active = db.scalar(select(VocabAttempt).where(VocabAttempt.student_id == user.id, VocabAttempt.unit_id == u.id,
                                                  VocabAttempt.status == "in_progress")
                       .order_by(VocabAttempt.id.desc()).limit(1))
    if active:
        return {"attempt_id": active.id, "unit_number": u.unit_number, "answers": active.answers or {},
                "warning_limit": cfg.vocab_warning_limit, "questions": _public_questions(active.questions)}
    done = db.scalars(select(VocabAttempt).where(VocabAttempt.student_id == user.id, VocabAttempt.unit_id == u.id,
                                                 VocabAttempt.status == "finished").order_by(VocabAttempt.id)).all()
    last = done[-1] if done else None
    retake = db.scalar(select(VocabRetake).where(VocabRetake.student_id == user.id, VocabRetake.unit_id == u.id,
                                                 VocabRetake.status == "approved", VocabRetake.used.is_(False)).limit(1))
    # 3 imkoniyat: o'tolmasa o'zi qayta topshiradi; o'tgan / chiqarilgan / 3 urinish tugagan bo'lsa o'qituvchi ruxsati kerak
    needs_retake = bool(last) and (last.passed or last.kicked_out or len(done) >= MAX_UNIT_ATTEMPTS)
    if needs_retake and not retake:
        raise AppError(409, "vocab_attempt_done" if (last.passed or last.kicked_out) else "vocab_attempts_over")
    if len(u.words or []) < 1:
        raise AppError(400, "vocab_no_words")
    if retake and needs_retake:
        retake.used = True
    attempt = VocabAttempt(unit_id=u.id, student_id=user.id, questions=_build_questions(u.words))
    db.add(attempt)
    db.commit()
    return {"attempt_id": attempt.id, "unit_number": u.unit_number, "warning_limit": cfg.vocab_warning_limit,
            "questions": _public_questions(attempt.questions)}


def _own_attempt(db: Session, attempt_id: int, user: User) -> VocabAttempt:
    a = db.get(VocabAttempt, attempt_id)
    if not a or a.student_id != user.id:
        raise AppError(404, "not_found")
    return a


class ViolationIn(BaseModel):
    kind: str = Field(max_length=40)  # tab_switch | blur | fullscreen_exit | copy | paste | context_menu | print | key
    answers: Dict[str, Union[int, str]] = Field(default_factory=dict)  # chiqarilsa, shu paytgacha berilgan javoblar saqlanadi


@router.post("/attempts/{attempt_id}/violation")
def violation(attempt_id: int, data: ViolationIn, db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    a = _own_attempt(db, attempt_id, user)
    _, b = _unit_book(db, a.unit_id)
    cfg = scoring.get_teacher_settings(db, b.teacher_id)
    limit = int(cfg.vocab_warning_limit)
    if a.status != "in_progress":
        return {"warnings": a.warnings_count, "limit": limit, "remaining": 0, "kicked_out": a.kicked_out, "finished": True}
    a.warnings_count += 1
    a.violations = [*(a.violations or []), {"kind": data.kind[:40], "at": iso(utcnow())}]
    kicked = a.warnings_count > limit  # limit ta ogohlantirishdan keyingi navbatdagi qoidabuzarlikda chiqariladi
    if kicked:
        _finish(db, a, data.answers, cfg.vocab_pass_percent, kicked=True)
    db.commit()
    return {"warnings": a.warnings_count, "limit": limit, "remaining": max(0, limit - a.warnings_count),
            "kicked_out": kicked, "finished": kicked}


class AnswerIn(BaseModel):
    question_id: int
    value: int


@router.post("/attempts/{attempt_id}/answer")
def answer_question(attempt_id: int, data: AnswerIn, db: Session = Depends(get_db),
                    user: User = Depends(require_role("student"))):
    """Javobni saqlaydi (bir marta). 3 ta xato bo'lsa imtihon avtomatik to'xtatiladi."""
    a = _own_attempt(db, attempt_id, user)
    if a.status != "in_progress":
        return {"stopped": a.stopped, "finished": True, "mistakes": a.mistakes}
    q = next((x for x in a.questions if x["id"] == data.question_id), None)
    if q is None:
        raise AppError(404, "not_found")
    answers = dict(a.answers or {})
    key = str(q["id"])
    if key in answers:  # javob qulflangan
        return {"stopped": False, "finished": False, "mistakes": a.mistakes, "locked": True}
    answers[key] = data.value
    a.answers = answers
    if not _is_correct(q, data.value):
        a.mistakes = (a.mistakes or 0) + 1
    stopped = a.mistakes >= MAX_MISTAKES
    if stopped:
        u, b = _unit_book(db, a.unit_id)
        cfg = scoring.get_teacher_settings(db, b.teacher_id)
        a.stopped = True
        _finish(db, a, answers, cfg.vocab_pass_percent)
        a.passed, a.score = False, 0.0
        db.flush()
        scoring.recalculate(db, a.student_id)
    db.commit()
    return {"stopped": stopped, "finished": stopped, "mistakes": a.mistakes}


class SubmitIn(BaseModel):
    answers: Dict[str, Union[int, str]] = Field(default_factory=dict)


@router.post("/attempts/{attempt_id}/submit")
def submit_exam(attempt_id: int, data: SubmitIn, db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    a = _own_attempt(db, attempt_id, user)
    if a.status != "in_progress":
        raise AppError(409, "vocab_finished")
    u, b = _unit_book(db, a.unit_id)
    cfg = scoring.get_teacher_settings(db, b.teacher_id)
    _finish(db, a, {**data.answers, **(a.answers or {})}, cfg.vocab_pass_percent)
    db.commit()
    return {**_a_out(a, u, b), "found": a.found, "missed": a.missed}


class RetakeIn(BaseModel):
    unit_id: int
    reason: str = Field(min_length=5, max_length=500)


def _r_out(r: VocabRetake, unit: VocabUnit, book: Book, student_name: Optional[str] = None) -> dict:
    return {"id": r.id, "kind": "vocab", "unit_id": r.unit_id, "unit_number": unit.unit_number, "unit_title": unit.title,
            "test_title": f"{book.title} · Unit {unit.unit_number}", "student_id": r.student_id, "student_name": student_name,
            "reason": r.reason, "status": r.status, "teacher_note": r.teacher_note, "used": r.used,
            "created_at": iso(r.created_at), "resolved_at": iso(r.resolved_at)}


@router.post("/retake")
def request_retake(data: RetakeIn, db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    u, b = _student_unit(db, data.unit_id, user)
    last = db.scalar(select(VocabAttempt).where(VocabAttempt.student_id == user.id, VocabAttempt.unit_id == u.id,
                                                VocabAttempt.status == "finished").order_by(VocabAttempt.id.desc()).limit(1))
    if not last:
        raise AppError(400, "vocab_retake_not_needed")
    open_req = db.scalar(select(VocabRetake.id).where(VocabRetake.student_id == user.id, VocabRetake.unit_id == u.id,
                                                      VocabRetake.status.in_(["pending", "approved"]), VocabRetake.used.is_(False)))
    if open_req:
        raise AppError(409, "retake_pending")
    r = VocabRetake(unit_id=u.id, student_id=user.id, attempt_id=last.id, reason=data.reason.strip())
    db.add(r)
    db.commit()
    return _r_out(r, u, b, user.name)


@router.get("/retake/mine")
def my_retakes(db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    rows = db.execute(select(VocabRetake, VocabUnit, Book).join(VocabUnit, VocabUnit.id == VocabRetake.unit_id)
                      .join(Book, Book.id == VocabUnit.book_id).where(VocabRetake.student_id == user.id)
                      .order_by(VocabRetake.id.desc())).all()
    return [_r_out(r, u, b, user.name) for r, u, b in rows]


# ---------- O'qituvchi ----------

@router.get("/retake")
def list_retakes(status: Optional[str] = None, db: Session = Depends(get_db), user: User = Depends(require_role("teacher"))):
    stmt = (select(VocabRetake, VocabUnit, Book, User.name).join(VocabUnit, VocabUnit.id == VocabRetake.unit_id)
            .join(Book, Book.id == VocabUnit.book_id).join(User, User.id == VocabRetake.student_id)
            .where(Book.group_id.in_(teacher_group_ids(db, user) or [0])))
    if status in ("pending", "approved", "rejected"):
        stmt = stmt.where(VocabRetake.status == status)
    return [_r_out(r, u, b, n) for r, u, b, n in db.execute(stmt.order_by(VocabRetake.id.desc())).all()]


class ResolveIn(BaseModel):
    note: Optional[str] = Field(default=None, max_length=500)


def _resolve(db: Session, retake_id: int, user: User, status: str, note: Optional[str]) -> dict:
    r = db.get(VocabRetake, retake_id)
    if not r:
        raise AppError(404, "not_found")
    u, b = _unit_book(db, r.unit_id)
    get_group_for_teacher(db, b.group_id, user)
    if r.status != "pending":
        raise AppError(409, "request_resolved")
    r.status, r.resolved_at, r.teacher_note = status, utcnow(), (note or "").strip() or None
    db.commit()
    student = db.get(User, r.student_id)
    return _r_out(r, u, b, student.name if student else None)


@router.post("/retake/{retake_id}/approve")
def approve_retake(retake_id: int, data: ResolveIn = ResolveIn(), db: Session = Depends(get_db),
                   user: User = Depends(require_role("teacher"))):
    return _resolve(db, retake_id, user, "approved", data.note)


@router.post("/retake/{retake_id}/reject")
def reject_retake(retake_id: int, data: ResolveIn = ResolveIn(), db: Session = Depends(get_db),
                  user: User = Depends(require_role("teacher"))):
    return _resolve(db, retake_id, user, "rejected", data.note)


@router.get("/attempts")
def list_attempts(group_id: Optional[int] = None, unit_id: Optional[int] = None, db: Session = Depends(get_db),
                  user: User = Depends(require_role("teacher"))):
    gids = [group_id] if group_id else teacher_group_ids(db, user)
    if group_id:
        get_group_for_teacher(db, group_id, user)
    stmt = (select(VocabAttempt, VocabUnit, Book, User).join(VocabUnit, VocabUnit.id == VocabAttempt.unit_id)
            .join(Book, Book.id == VocabUnit.book_id).join(User, User.id == VocabAttempt.student_id)
            .where(Book.group_id.in_(gids or [0]), VocabAttempt.status == "finished"))
    if unit_id:
        stmt = stmt.where(VocabAttempt.unit_id == unit_id)
    names = dict(db.execute(select(Group.id, Group.name)).all())
    out = []
    for a, u, b, s in db.execute(stmt.order_by(VocabAttempt.id.desc()).limit(500)).all():
        d = _a_out(a, u, b, s)
        d["group_name"] = names.get(b.group_id)
        out.append(d)
    return out


def _teacher_attempt(db: Session, attempt_id: int, user: User):
    a = db.get(VocabAttempt, attempt_id)
    if not a:
        raise AppError(404, "not_found")
    u, b = _unit_book(db, a.unit_id)
    get_group_for_teacher(db, b.group_id, user)
    return a, u, b


@router.get("/attempts/{attempt_id}")
def attempt_detail(attempt_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("teacher"))):
    a, u, b = _teacher_attempt(db, attempt_id, user)
    student = db.get(User, a.student_id)
    return {**_a_out(a, u, b, student), "found": a.found or [], "missed": a.missed or [],
            "violations": a.violations or []}


# ---------- Yakuniy test (barcha unitlar topshirilgach) ----------

FINAL_WORDS = 100        # 100 ta so'z
FINAL_MAX_MISTAKES = 10  # 10 tagacha xato mumkin; 11-xatoda to'xtaydi
FINAL_ATTEMPTS = 3
FINAL_SCORE = 25.0


def _student_book(db: Session, book_id: int, user: User) -> Book:
    b = db.get(Book, book_id)
    if not b:
        raise AppError(404, "not_found")
    if not is_member(db, b.group_id, user.id):
        raise AppError(403, "book_not_available")
    return b


def _final_words(db: Session, book: Book) -> List[dict]:
    """Kitobning barcha unitlaridan 100 ta so'z. Tanlov kitobga bog'langan (doim bir xil), shuning uchun
    "yodlash" ro'yxati va test aynan bir xil so'zlardan iborat bo'ladi."""
    seen, pool = set(), []
    for u in sorted(book.units, key=lambda x: (x.unit_number, x.id)):
        for w in u.words or []:
            key = (w.get("en") or "").strip().lower()
            if key and w.get("uz") and key not in seen:
                seen.add(key)
                pool.append({"en": w["en"], "uz": w["uz"]})
    rnd = random.Random(book.id)
    return rnd.sample(pool, FINAL_WORDS) if len(pool) > FINAL_WORDS else pool


def _final_questions(words: List[dict]) -> List[dict]:
    translations = list(dict.fromkeys(w["uz"] for w in words))
    pool = list(words)
    random.shuffle(pool)
    out = []
    for w in pool:
        options = [w["uz"], *random.sample([x for x in translations if x != w["uz"]],
                                           min(3, max(0, len(translations) - 1)))]
        random.shuffle(options)
        out.append({"id": len(out), "word": w["en"], "uz": w["uz"], "type": "choice",
                    "options": options, "correct_index": options.index(w["uz"])})
    return out


def _passed_unit_ids(db: Session, user_id: int, book_id: int) -> set:
    return set(db.scalars(select(VocabAttempt.unit_id).join(VocabUnit, VocabUnit.id == VocabAttempt.unit_id)
                          .where(VocabAttempt.student_id == user_id, VocabUnit.book_id == book_id,
                                 VocabAttempt.status == "finished", VocabAttempt.passed.is_(True))).all())


def _final_state(db: Session, book: Book, user: User) -> dict:
    unit_ids = {u.id for u in book.units}
    passed = len(unit_ids & _passed_unit_ids(db, user.id, book.id))
    finals = db.scalars(select(VocabFinalAttempt).where(VocabFinalAttempt.book_id == book.id, VocabFinalAttempt.student_id == user.id,
                                                        VocabFinalAttempt.status == "finished")
                        .order_by(VocabFinalAttempt.id)).all()
    won = any(f.passed for f in finals)
    return {"book_id": book.id, "book_title": book.title, "units_total": len(unit_ids), "units_passed": passed,
            "unlocked": bool(unit_ids) and passed >= len(unit_ids), "passed": won,
            "score": max((f.score for f in finals), default=0.0), "attempts_used": len(finals),
            "attempts_left": 0 if won else max(0, FINAL_ATTEMPTS - len(finals)),
            "words_count": len(_final_words(db, book)), "max_mistakes": FINAL_MAX_MISTAKES, "reward": FINAL_SCORE}


@router.get("/final")
def my_finals(db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    books = db.scalars(select(Book).where(Book.group_id.in_(student_group_ids(db, user.id) or [0]))
                       .order_by(Book.id)).all()
    return [_final_state(db, b, user) for b in books if b.units]


@router.get("/final/{book_id}/words")
def final_words(book_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    b = _student_book(db, book_id, user)
    if not _final_state(db, b, user)["unlocked"]:
        raise AppError(403, "final_locked")
    return {"book_title": b.title, "words": _final_words(db, b)}


def _final_public(a: VocabFinalAttempt) -> dict:
    return {"attempt_id": a.id, "answers": a.answers or {}, "max_mistakes": FINAL_MAX_MISTAKES,
            "questions": _public_questions(a.questions)}


class FinalStartIn(BaseModel):
    strict: bool = False  # ixtiyoriy qat'iy rejim (full screen + ogohlantirishlar)


@router.post("/final/{book_id}/start")
def final_start(book_id: int, data: FinalStartIn = FinalStartIn(), db: Session = Depends(get_db),
                user: User = Depends(require_role("student"))):
    b = _student_book(db, book_id, user)
    st = _final_state(db, b, user)
    if not st["unlocked"]:
        raise AppError(403, "final_locked")
    active = db.scalar(select(VocabFinalAttempt).where(VocabFinalAttempt.book_id == b.id, VocabFinalAttempt.student_id == user.id,
                                                       VocabFinalAttempt.status == "in_progress").order_by(VocabFinalAttempt.id.desc()).limit(1))
    if active:
        return _final_public(active)
    if st["passed"]:
        raise AppError(409, "final_done")
    if st["attempts_left"] <= 0:
        raise AppError(409, "final_attempts_over")
    attempt = VocabFinalAttempt(book_id=b.id, student_id=user.id, strict=data.strict,
                                questions=_final_questions(_final_words(db, b)))
    db.add(attempt)
    db.commit()
    return _final_public(attempt)


def _own_final(db: Session, attempt_id: int, user: User) -> VocabFinalAttempt:
    a = db.get(VocabFinalAttempt, attempt_id)
    if not a or a.student_id != user.id:
        raise AppError(404, "not_found")
    return a


def _final_finish(db: Session, a: VocabFinalAttempt, stopped: bool = False) -> None:
    total = len(a.questions) or 1
    answers = a.answers or {}
    correct = sum(1 for q in a.questions if str(q["id"]) in answers and _is_correct(q, answers[str(q["id"])]))
    a.mistakes = total - correct  # javob berilmaganlar ham xato hisoblanadi
    a.percent = round(correct * 100 / total, 1)
    a.stopped = stopped
    a.passed = (not stopped) and a.mistakes <= FINAL_MAX_MISTAKES
    a.score = FINAL_SCORE if a.passed else 0.0
    a.status = "finished"
    a.finished_at = utcnow()
    db.flush()
    scoring.recalculate(db, a.student_id)


def _final_result(a: VocabFinalAttempt) -> dict:
    answers = a.answers or {}
    missed = [{"en": q["word"], "uz": q["uz"]} for q in a.questions
              if not (str(q["id"]) in answers and _is_correct(q, answers[str(q["id"])]))]
    return {"id": a.id, "passed": a.passed, "stopped": a.stopped, "score": a.score, "percent": a.percent,
            "mistakes": a.mistakes, "warnings_count": a.warnings_count,
            "found": [None] * (len(a.questions) - len(missed)), "missed": missed}


@router.post("/final-attempts/{attempt_id}/answer")
def final_answer(attempt_id: int, data: AnswerIn, db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    a = _own_final(db, attempt_id, user)
    if a.status != "in_progress":
        return {"stopped": a.stopped, "finished": True, "mistakes": a.mistakes}
    q = next((x for x in a.questions if x["id"] == data.question_id), None)
    if q is None:
        raise AppError(404, "not_found")
    answers = dict(a.answers or {})
    key = str(q["id"])
    if key in answers:
        return {"stopped": False, "finished": False, "mistakes": a.mistakes, "locked": True}
    answers[key] = data.value
    a.answers = answers
    if not _is_correct(q, data.value):
        a.mistakes = (a.mistakes or 0) + 1
    stopped = a.mistakes > FINAL_MAX_MISTAKES
    if stopped:
        _final_finish(db, a, stopped=True)
    db.commit()
    return {"stopped": stopped, "finished": stopped, "mistakes": a.mistakes}


@router.post("/final-attempts/{attempt_id}/submit")
def final_submit(attempt_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    a = _own_final(db, attempt_id, user)
    if a.status != "in_progress":
        raise AppError(409, "vocab_finished")
    _final_finish(db, a)
    db.commit()
    return _final_result(a)


@router.post("/final-attempts/{attempt_id}/violation")
def final_violation(attempt_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    """Qat'iy rejimda qoidabuzarlik: faqat ogohlantirish beriladi va sanaladi (imtihon to'xtatilmaydi)."""
    a = _own_final(db, attempt_id, user)
    if a.status == "in_progress":
        a.warnings_count = (a.warnings_count or 0) + 1
        db.commit()
    return {"warnings": a.warnings_count}
