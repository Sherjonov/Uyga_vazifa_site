"""Ota-onalarga avtomatik Telegram xabarlari: davomat, topshirilmagan uyga vazifa va xavf zonasi.

Har bir hodisa uchun xabar bir marta yuboriladi (ParentAlert jurnali). Davomat o'qituvchi belgilagan zahoti ketadi;
topshirilmagan vazifa va xavf zonasi esa fon oqimida har ALERTS_INTERVAL_MINUTES daqiqada tekshiriladi."""
import threading
import traceback
from datetime import date as date_type, timedelta
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from config import settings
from database import SessionLocal
from models.assignment import Assignment, Submission
from models.attendance import Attendance
from models.automation import DangerZoneState, ParentAlert
from models.group import Group, GroupMember
from models.telegram import ParentLink, TelegramAccount
from models.user import User
from services import scoring, student_automation
from services import telegram_api as tg
from services.child_stats import fmt_dt, num
from services.telegram_api import esc
from utils import utcnow

HW_WINDOW_DAYS = 3  # shu kunlardan eski muddati o'tgan vazifalar haqida xabar yuborilmaydi

ATTENDANCE_TEXT = {
    "present": "✅ Farzandingiz <b>{name}</b> bugun darsga <b>keldi</b>.",
    "late": "⏰ Farzandingiz <b>{name}</b> darsga <b>kech qolib keldi</b>.{pen}",
    "absent": "❌ Farzandingiz <b>{name}</b> bugun darsga <b>kelmadi</b>.{pen}",
    "excused": "🟡 Farzandingiz <b>{name}</b> bugun darsga <b>sababli kelmadi</b>.",
}

DANGER_REASONS = {
    "missed_homework": lambda r: f"🏠 {r['value']} ta uyga vazifa topshirilmagan",
    "low_tests": lambda r: f"📝 testlarning o'rtacha bali past ({num(r['value'])}/10)",
    "absences": lambda r: f"📅 {r['value']} marta sababsiz darsga kelmagan",
    "score_drop": lambda r: f"📉 so'nggi 2 haftada {num(r['value'])} ball kamaygan",
    "inactive": lambda r: "💤 saytga uzoq vaqt kirmagan" + (f" ({r['value']} kun)" if r.get("value") else ""),
}


def parent_accounts(db: Session, student_id: int) -> List[TelegramAccount]:
    return list(db.scalars(
        select(TelegramAccount).join(ParentLink, ParentLink.telegram_account_id == TelegramAccount.id)
        .where(ParentLink.student_id == student_id, TelegramAccount.blocked.is_(False))).all())


def send_to_parents(db: Session, student_id: int, text: str) -> int:
    sent = 0
    for acc in parent_accounts(db, student_id):
        r = tg.send_text(acc.chat_id, text)
        if r["ok"]:
            sent += 1
        elif r["blocked"]:
            acc.blocked = True
    return sent


def alert_parents(db: Session, student_id: int, kind: str, ref: str, text: str) -> int:
    """Bir marta yuboradi (kind+ref bo'yicha). Yuborilgan ota-onalar sonini qaytaradi."""
    if db.scalar(select(ParentAlert.id).where(ParentAlert.student_id == student_id, ParentAlert.kind == kind, ParentAlert.ref == ref)):
        return 0
    db.add(ParentAlert(student_id=student_id, kind=kind, ref=ref))
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        return 0
    return send_to_parents(db, student_id, text)


# ───────────────────────── davomat ─────────────────────────

def _notify_attendance(group_id: int, student_id: int, day: date_type, status: Optional[str]) -> None:
    if not status or status not in ATTENDANCE_TEXT or not tg.is_configured():
        return
    with SessionLocal() as db:
        student, group = db.get(User, student_id), db.get(Group, group_id)
        row = db.scalar(select(Attendance).where(Attendance.group_id == group_id, Attendance.student_id == student_id,
                                                 Attendance.date == day))
        if not student or not group:
            return
        penalty = float(row.penalty_applied or 0) if row else 0.0
        text = ATTENDANCE_TEXT[status].format(name=esc(student.name), pen=f" Jarima: <b>−{num(penalty)}</b> ball." if penalty else "")
        text += f"\n👥 {esc(group.name)} · 📆 {day.strftime('%d.%m.%Y')}"
        alert_parents(db, student_id, "attendance", f"{group_id}:{day.isoformat()}:{status}", text)
        db.commit()


def notify_attendance_async(group_id: int, student_id: int, day: date_type, status: Optional[str]) -> None:
    """Davomat belgilanganda ota-onaga avtomatik xabar (so'rovni sekinlashtirmaslik uchun alohida oqimda)."""
    if not status or not tg.is_configured():
        return

    def run() -> None:
        try:
            _notify_attendance(group_id, student_id, day, status)
        except Exception:  # noqa: BLE001
            traceback.print_exc()

    threading.Thread(target=run, daemon=True, name="tg-attendance").start()


# ───────────────────────── topshirilmagan uyga vazifa ─────────────────────────

def check_missed_homework(db: Session) -> int:
    now = utcnow()
    sent = 0
    assignments = db.scalars(select(Assignment).where(
        Assignment.kind == "homework", Assignment.due_at.is_not(None), Assignment.due_at < now,
        Assignment.due_at > now - timedelta(days=HW_WINDOW_DAYS))).all()
    for a in assignments:
        group = db.get(Group, a.group_id)
        penalty = float(scoring.get_teacher_settings(db, a.teacher_id).hw_missing_penalty or 0)
        done = set(db.scalars(select(Submission.student_id).where(
            Submission.assignment_id == a.id, Submission.submitted_at.is_not(None))).all())
        members = db.scalars(select(User).join(GroupMember, GroupMember.student_id == User.id)
                             .where(GroupMember.group_id == a.group_id, User.role == "student", User.is_active.is_(True))).all()
        for s in members:
            if s.id in done:
                continue
            text = (f"❌ Farzandingiz <b>{esc(s.name)}</b> «{esc(a.title[:70])}» uyga vazifasini <b>topshirmadi</b>"
                    f" (muddat: {fmt_dt(a.due_at)})." + (f" Jarima: <b>−{num(penalty)}</b> ball." if penalty else ""))
            if group:
                text += f"\n👥 {esc(group.name)}"
            sent += alert_parents(db, s.id, "hw_missed", str(a.id), text)
    db.commit()
    return sent


# ───────────────────────── xavf zonasi ─────────────────────────

def check_danger_zone(db: Session) -> int:
    sent = 0
    for teacher in db.scalars(select(User).where(User.role == "teacher", User.is_active.is_(True))).all():
        rows = student_automation.danger_zone(db, teacher)
        in_zone = {r["student"]["id"]: r for r in rows}
        states = {s.student_id: s for s in db.scalars(select(DangerZoneState).where(DangerZoneState.teacher_id == teacher.id)).all()}
        for sid, row in in_zone.items():
            state = states.get(sid)
            if not state:
                state = DangerZoneState(teacher_id=teacher.id, student_id=sid, active=False, notified=False)
                db.add(state)
            state.active = True
            if state.notified:
                continue
            reasons = "\n".join("· " + DANGER_REASONS[r["code"]](r) for r in row["reasons"] if r["code"] in DANGER_REASONS)
            text = (f"⚠️ <b>Diqqat!</b> Farzandingiz <b>{esc(row['student']['name'])}</b> ({esc(row['group']['name'])}) "
                    f"<b>xavf zonasiga tushdi</b>.\n\nSabablari:\n{reasons}\n\n"
                    "O'qituvchi bilan bog'lanish: /oqituvchiga_xabar · Holati: /status")
            sent += send_to_parents(db, sid, text)
            state.notified = True
        for sid, state in states.items():
            if sid not in in_zone and state.active:  # xavfdan chiqdi: qayta tushsa yana xabar boradi
                state.active, state.notified = False, False
        db.commit()
    return sent


def run_cycle() -> None:
    from services import telegram_bot
    if not tg.is_configured() or not telegram_bot.owns_lock():  # faqat botni ushlab turgan jarayon yuboradi (ikki marta xabar bormasin)
        return
    with SessionLocal() as db:
        check_missed_homework(db)
    with SessionLocal() as db:
        check_danger_zone(db)


# ───────────────────────── fon oqimi ─────────────────────────

_stop = threading.Event()
_thread: Optional[threading.Thread] = None


def _loop() -> None:
    _stop.wait(30)  # server to'liq ishga tushishini kutamiz
    while not _stop.is_set():
        try:
            run_cycle()
        except Exception:  # noqa: BLE001 — bitta xato fon oqimini to'xtatmasin
            traceback.print_exc()
        _stop.wait(max(1, settings.ALERTS_INTERVAL_MINUTES) * 60)


def start() -> bool:
    global _thread
    if not tg.is_configured():
        return False
    if _thread and _thread.is_alive():
        return True
    _stop.clear()
    _thread = threading.Thread(target=_loop, name="parent-alerts", daemon=True)
    _thread.start()
    return True


def stop() -> None:
    _stop.set()
