import tempfile
from datetime import timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from deps import (get_db, require_role, get_group_for_teacher, is_member, student_group_ids, teacher_group_ids)
from messages import AppError
from models.group import GroupMember
from models.test import Test, Question, TestAttempt, RetakeRequest
from models.user import User
from schemas.test import TestCreate, TestUpdate, AnswersIn, TestGenerateIn, TestReplaceIn
from services import ai_service, scoring, storage
from services.pdf_service import pdf_to_text
from services.test_parser import parse_questions
from utils import iso, utcnow

router = APIRouter(prefix="/tests", tags=["tests"])


def _q_out(q: Question, with_answer: bool) -> dict:
    d = {"id": q.id, "text": q.text, "options": q.options, "position": q.position}
    if with_answer:
        d["correct_index"] = q.correct_index
        d["explanation"] = q.explanation
    return d


def _t_out(t: Test, with_questions: bool = False) -> dict:
    d = {"id": t.id, "group_id": t.group_id, "title": t.title, "duration_minutes": t.duration_minutes,
         "is_published": t.is_published, "created_at": iso(t.created_at), "questions_count": len(t.questions)}
    if with_questions:
        d["questions"] = [_q_out(q, True) for q in t.questions]
    return d


def _get_test(db: Session, test_id: int) -> Test:
    t = db.get(Test, test_id)
    if not t:
        raise AppError(404, "not_found")
    return t


def _replace_questions(db: Session, t: Test, questions) -> None:
    for q in list(t.questions):
        db.delete(q)
    db.flush()
    for i, q in enumerate(questions, 1):
        db.add(Question(test_id=t.id, position=i, text=q.text.strip(), options=q.options, correct_index=q.correct_index,
                        explanation=(q.explanation or '').strip() or None))


# ---------- O'qituvchi ----------

@router.post("/parse")
def parse_pdf(file: UploadFile = File(...), user: User = Depends(require_role("teacher", "admin"))):
    """PDF dan savollarni ajratadi (saqlamaydi). O'qituvchi ko'rib chiqib tahrirlaydi."""
    rel = storage.save_upload(file, "pdfs", {".pdf"}, max_mb=30)
    try:
        text = pdf_to_text(storage.abs_path(rel))
    except Exception:
        raise AppError(400, "bad_pdf")
    finally:
        storage.delete_file(rel)
    if len(text.strip()) < 20:
        raise AppError(400, "pdf_no_text")
    questions, method = parse_questions(text)
    if not questions:
        raise AppError(400, "no_questions")
    return {"method": method, "questions": questions}


@router.post("/generate")
def generate_test(data: TestGenerateIn, user: User = Depends(require_role("teacher", "admin"))):
    """AI mavzu bo'yicha aynan `count` ta savol va har birida `options_count` ta variant tuzadi (saqlanmaydi: o'qituvchi tahrirlaydi)."""
    if not ai_service.is_configured():
        raise AppError(503, "ai_not_configured")
    try:
        ai_service.validate_model_choice(data.model)
        questions = ai_service.generate_test(data.topic.strip(), data.count, data.options_count, data.model)
    except ai_service.AIError as e:
        raise AppError(503, e.code) from e
    return {"method": "ai", "questions": questions}


@router.post("/generate/replace")
def replace_question(data: TestReplaceIn, user: User = Depends(require_role("teacher", "admin"))):
    """Bitta savolni yangisiga almashtirish (oldingilari takrorlanmaydi)."""
    if not ai_service.is_configured():
        raise AppError(503, "ai_not_configured")
    try:
        ai_service.validate_model_choice(data.model)
        q = ai_service.generate_test(data.topic.strip(), 1, data.options_count, data.model, avoid=data.avoid)[0]
    except ai_service.AIError as e:
        raise AppError(503, e.code) from e
    return {"question": q}


@router.post("")
def create_test(data: TestCreate, db: Session = Depends(get_db), user: User = Depends(require_role("teacher", "admin"))):
    get_group_for_teacher(db, data.group_id, user)
    t = Test(group_id=data.group_id, teacher_id=user.id, title=data.title.strip(),
             duration_minutes=data.duration_minutes, is_published=data.is_published)
    db.add(t)
    db.flush()
    _replace_questions(db, t, data.questions)
    db.commit()
    db.refresh(t)
    return _t_out(t, True)


@router.get("")
def list_tests(group_id: Optional[int] = None, db: Session = Depends(get_db), user: User = Depends(require_role("teacher", "admin"))):
    if group_id:
        get_group_for_teacher(db, group_id, user)
        gids = [group_id]
    else:
        gids = teacher_group_ids(db, user)
    tests = db.scalars(select(Test).where(Test.group_id.in_(gids or [0])).order_by(Test.created_at.desc())).all()
    pending = dict(db.execute(select(RetakeRequest.test_id, func.count()).where(RetakeRequest.status == "pending").group_by(RetakeRequest.test_id)).all())
    finished = dict(db.execute(select(TestAttempt.test_id, func.count()).where(
        TestAttempt.status == "finished", TestAttempt.counted.is_(True)).group_by(TestAttempt.test_id)).all())
    out = []
    for t in tests:
        d = _t_out(t)
        d.update({"pending_retakes": pending.get(t.id, 0), "finished_count": finished.get(t.id, 0)})
        out.append(d)
    return out


@router.get("/mine")
def my_tests(db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    gids = student_group_ids(db, user.id)
    tests = db.scalars(select(Test).where(Test.group_id.in_(gids or [0]), Test.is_published.is_(True)).order_by(Test.created_at.desc())).all()
    now = utcnow()
    out = []
    for t in tests:
        scoring.expire_stale_attempts(db, t.id, user.id, now)
        attempts = db.scalars(select(TestAttempt).where(TestAttempt.test_id == t.id, TestAttempt.student_id == user.id)
                              .order_by(TestAttempt.id)).all()
        req = db.scalar(select(RetakeRequest).where(RetakeRequest.test_id == t.id, RetakeRequest.student_id == user.id)
                        .order_by(RetakeRequest.id.desc()).limit(1))
        counted = next((a for a in attempts if a.status == "finished" and a.counted), None)
        active = next((a for a in attempts if a.status == "in_progress"), None)
        has_unfinished = any(a.status == "expired" for a in attempts)
        approved_unused = bool(req and req.status == "approved" and not req.used)
        if counted:
            state = "finished"
        elif active:
            state = "in_progress"
        elif has_unfinished:
            state = "retake_approved" if approved_unused else "needs_retake"
        else:
            state = "available"
        d = _t_out(t)
        d.update({
            "state": state,
            "score": counted.score if counted else None,
            "percent": counted.percent if counted else None,
            "retake_status": req.status if req and not req.used else None,
            "retake_request_id": req.id if req else None,
            "can_practice": bool(counted),
        })
        out.append(d)
    db.commit()
    return out


@router.get("/attempts/{attempt_id}/result")
def attempt_result(attempt_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    a = db.get(TestAttempt, attempt_id)
    if not a or a.student_id != user.id:
        raise AppError(404, "attempt_not_found")
    return _result(a)


@router.put("/attempts/{attempt_id}/answers")
def save_answers(attempt_id: int, data: AnswersIn, db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    a = db.get(TestAttempt, attempt_id)
    if not a or a.student_id != user.id:
        raise AppError(404, "attempt_not_found")
    if a.status != "in_progress" or utcnow() > a.deadline_at + timedelta(seconds=scoring.ATTEMPT_GRACE_SECONDS):
        raise AppError(400, "test_time_over")
    a.answers = {str(k): int(v) for k, v in data.answers.items()}
    db.commit()
    return {"saved": len(a.answers)}


@router.post("/attempts/{attempt_id}/finish")
def finish_attempt(attempt_id: int, data: AnswersIn, db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    a = db.get(TestAttempt, attempt_id)
    if not a or a.student_id != user.id:
        raise AppError(404, "attempt_not_found")
    if a.status == "finished":
        return _result(a)
    if a.status != "in_progress":
        raise AppError(400, "test_time_over")
    now = utcnow()
    if now > a.deadline_at + timedelta(seconds=scoring.ATTEMPT_GRACE_SECONDS):
        a.status = "expired"
        db.commit()
        raise AppError(400, "test_time_over")

    answers = {str(k): int(v) for k, v in (data.answers or a.answers or {}).items()}
    questions = db.scalars(select(Question).where(Question.test_id == a.test_id)).all()
    correct = sum(1 for q in questions if answers.get(str(q.id)) == q.correct_index)
    total = len(questions)
    a.answers = answers
    a.correct_count = correct
    a.total = total
    a.percent = round(correct / total * 100, 2) if total else 0.0
    a.score = round(a.percent / 10, 2)  # 100% = 10 ball, 95% = 9.5 ball
    a.status = "finished"
    a.finished_at = now
    if a.counted:
        scoring.recalculate(db, user.id)
    db.commit()
    return _result(a)


def _result(a: TestAttempt) -> dict:
    return {"attempt_id": a.id, "test_id": a.test_id, "status": a.status, "counted": a.counted,
            "correct": a.correct_count, "total": a.total, "percent": a.percent,
            "score": a.score if a.counted else None, "practice_score": None if a.counted else a.score,
            "finished_at": iso(a.finished_at)}


def _attempt_payload(db: Session, t: Test, a: TestAttempt) -> dict:
    qs = db.scalars(select(Question).where(Question.test_id == t.id).order_by(Question.position)).all()
    return {"attempt_id": a.id, "counted": a.counted, "started_at": iso(a.started_at), "deadline_at": iso(a.deadline_at),
            "server_time": iso(utcnow()), "answers": a.answers or {},
            "test": {"id": t.id, "title": t.title, "duration_minutes": t.duration_minutes},
            "questions": [_q_out(q, False) for q in qs]}


@router.post("/{test_id}/start")
def start_attempt(test_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    t = _get_test(db, test_id)
    if not t.is_published or not is_member(db, t.group_id, user.id):
        raise AppError(403, "test_not_available")
    now = utcnow()
    scoring.expire_stale_attempts(db, t.id, user.id, now)
    attempts = db.scalars(select(TestAttempt).where(TestAttempt.test_id == t.id, TestAttempt.student_id == user.id)).all()

    active = next((a for a in attempts if a.status == "in_progress"), None)
    if active:
        db.commit()
        return _attempt_payload(db, t, active)

    counted_exists = any(a.status == "finished" and a.counted for a in attempts)
    unfinished = [a for a in attempts if a.status == "expired"]
    counted = True
    if counted_exists:
        counted = False  # mashq: ballni o'zgartirmaydi
    elif unfinished:
        req = db.scalar(select(RetakeRequest).where(
            RetakeRequest.test_id == t.id, RetakeRequest.student_id == user.id,
            RetakeRequest.status == "approved", RetakeRequest.used.is_(False)).order_by(RetakeRequest.id).limit(1))
        if not req:
            db.commit()
            raise AppError(403, "retake_required")
        req.used = True
        for a in unfinished:
            a.status = "voided"  # eski urinishlar bekor, yangisi "birinchi" hisoblanadi

    attempt = TestAttempt(test_id=t.id, student_id=user.id, counted=counted, started_at=now,
                          deadline_at=now + timedelta(minutes=t.duration_minutes), answers={})
    db.add(attempt)
    db.commit()
    return _attempt_payload(db, t, attempt)


@router.get("/{test_id}")
def get_test(test_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("teacher", "admin"))):
    t = _get_test(db, test_id)
    get_group_for_teacher(db, t.group_id, user)
    return _t_out(t, True)


@router.put("/{test_id}")
def update_test(test_id: int, data: TestUpdate, db: Session = Depends(get_db), user: User = Depends(require_role("teacher", "admin"))):
    t = _get_test(db, test_id)
    get_group_for_teacher(db, t.group_id, user)
    if data.title is not None:
        t.title = data.title.strip()
    if data.duration_minutes is not None:
        t.duration_minutes = data.duration_minutes
    if data.is_published is not None:
        t.is_published = data.is_published
    if data.questions is not None:
        _replace_questions(db, t, data.questions)
    db.commit()
    db.refresh(t)
    return _t_out(t, True)


@router.delete("/{test_id}")
def delete_test(test_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("teacher", "admin"))):
    t = _get_test(db, test_id)
    get_group_for_teacher(db, t.group_id, user)
    affected = {a.student_id for a in t.attempts}
    db.delete(t)
    db.flush()
    for sid in affected:
        scoring.recalculate(db, sid)
    db.commit()
    return {"ok": True}


@router.get("/{test_id}/results")
def test_results(test_id: int, db: Session = Depends(get_db), user: User = Depends(require_role("teacher", "admin"))):
    t = _get_test(db, test_id)
    get_group_for_teacher(db, t.group_id, user)
    students = db.scalars(select(User).join(GroupMember, GroupMember.student_id == User.id)
                          .where(GroupMember.group_id == t.group_id).order_by(User.name)).all()
    attempts = db.scalars(select(TestAttempt).where(TestAttempt.test_id == t.id)).all()
    by_student: dict = {}
    for a in attempts:
        by_student.setdefault(a.student_id, []).append(a)
    items = []
    for s in students:
        rows = by_student.get(s.id, [])
        counted = next((a for a in rows if a.status == "finished" and a.counted), None)
        items.append({"student": {"id": s.id, "name": s.name}, "attempts": len(rows),
                      "score": counted.score if counted else None, "percent": counted.percent if counted else None,
                      "status": "finished" if counted else (rows[-1].status if rows else "not_started")})
    return {"test": _t_out(t), "items": items}
