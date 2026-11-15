"""Ota-onalarga xabar yuborish (SMS / email) va xabar shablonlari."""
from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from messages import AppError
from models.assignment import Assignment, Submission
from models.attendance import Attendance
from models.group import GroupMember
from models.message import ParentMessage
from models.telegram import ParentLink, TelegramAccount
from models.test import TestAttempt
from models.user import User, ParentContact
from services import scoring
from services import telegram_api as tg
from services.email_service import send_email
from services.sms_service import send_sms
from utils import utcnow

TEMPLATES = {
    "uz": (
        "Assalomu alaykum! {name} haqida Learning English hisoboti:\n"
        "• Umumiy reyting balli: {total}\n"
        "• Testlar o'rtacha bali: {avg_test}\n"
        "• Sababsiz qoldirilgan darslar: {absent}, sababli: {excused}\n"
        "• Topshirilmagan uyga vazifalar: {missed}\n"
        "Iltimos, farzandingizning o'qishiga e'tibor bering."
    ),
    "en": (
        "Hello! Learning English report about {name}:\n"
        "• Total rating score: {total}\n"
        "• Average test score: {avg_test}\n"
        "• Unexcused absences: {absent}, excused: {excused}\n"
        "• Missed homework: {missed}\n"
        "Please pay attention to your child's studies."
    ),
    "ru": (
        "Здравствуйте! Отчёт Learning English о {name}:\n"
        "• Общий рейтинговый балл: {total}\n"
        "• Средний балл за тесты: {avg_test}\n"
        "• Пропуски без причины: {absent}, по причине: {excused}\n"
        "• Несданные домашние задания: {missed}\n"
        "Пожалуйста, обратите внимание на учёбу ребёнка."
    ),
}


def build_template(db: Session, student: User, group_ids: List[int], lang: str = "uz") -> str:
    bd = scoring.breakdown(db, student.id)
    avg = db.scalar(
        select(func.avg(TestAttempt.score)).where(
            TestAttempt.student_id == student.id, TestAttempt.status == "finished", TestAttempt.counted.is_(True)
        )
    )
    att = dict(
        db.execute(
            select(Attendance.status, func.count()).where(Attendance.student_id == student.id).group_by(Attendance.status)
        ).all()
    )
    now = utcnow()
    due_ids = list(
        db.scalars(
            select(Assignment.id).where(
                Assignment.group_id.in_(group_ids or [0]), Assignment.kind == "homework", Assignment.due_at < now
            )
        ).all()
    )
    done = 0
    if due_ids:
        done = db.scalar(
            select(func.count()).select_from(Submission).where(
                Submission.student_id == student.id, Submission.assignment_id.in_(due_ids), Submission.submitted_at.is_not(None)
            )
        )
    return TEMPLATES.get(lang, TEMPLATES["uz"]).format(
        name=student.name,
        total=bd["total"],
        avg_test=round(float(avg), 1) if avg is not None else "-",
        absent=att.get("absent", 0),
        excused=att.get("excused", 0),
        missed=max(0, len(due_ids) - int(done or 0)),
    )


def parent_accounts(db: Session, student_id: int) -> List[tuple]:
    """Farzandga botdan ulangan ota-onalar: [(ParentLink, TelegramAccount)]"""
    return db.execute(
        select(ParentLink, TelegramAccount).join(TelegramAccount, TelegramAccount.id == ParentLink.telegram_account_id)
        .where(ParentLink.student_id == student_id).order_by(ParentLink.id)
    ).all()


def parent_label(acc: TelegramAccount) -> str:
    return " · ".join(p for p in (acc.full_name, acc.phone or (f"@{acc.username}" if acc.username else None)) if p)[:255] or str(acc.chat_id)


def telegram_text(teacher: User, student: User, body: str) -> str:
    return (f"👨‍🏫 <b>{tg.esc(teacher.name)}</b> (o'qituvchi) xabari\n"
            f"👤 Farzand: <b>{tg.esc(student.name)}</b>\n\n{tg.esc(body)}")


def send_to_parent(db: Session, teacher: User, student: User, body: str, channel: str = "auto",
                   parent_link_id: Optional[int] = None) -> List[dict]:
    """Ota-onaga xabar: Telegram bot (ulangan ota-ona), SMS yoki email.
    parent_link_id berilsa faqat shu ota-onaning Telegram profiliga yuboriladi."""
    targets = []  # (kanal, qabul qiluvchi, chat_id)
    if parent_link_id is not None:
        row = db.execute(
            select(ParentLink, TelegramAccount).join(TelegramAccount, TelegramAccount.id == ParentLink.telegram_account_id)
            .where(ParentLink.id == parent_link_id, ParentLink.student_id == student.id)
        ).first()
        if not row:
            raise AppError(404, "parent_link_not_found")
        targets.append(("telegram", parent_label(row[1]), row[1].chat_id))
    else:
        contact = db.scalar(select(ParentContact).where(ParentContact.student_id == student.id))
        tg_accounts = parent_accounts(db, student.id) if channel in ("auto", "telegram") else []
        tg_phones = {acc.phone for _l, acc in tg_accounts if acc.phone}
        if contact:
            # Botga ulangan ota-onaga bir xil xabar SMS bilan ham bormasligi uchun
            if channel in ("auto", "sms") and contact.phone and not (channel == "auto" and contact.phone in tg_phones):
                targets.append(("sms", contact.phone, None))
            if channel in ("auto", "email") and contact.email:
                targets.append(("email", contact.email, None))
        for _link, acc in tg_accounts:
            targets.append(("telegram", parent_label(acc), acc.chat_id))
    if not targets:
        raise AppError(400, "no_parent_contact")

    results = []
    for ch, recipient, chat_id in targets:
        if ch == "telegram":
            r = tg.send_text(chat_id, telegram_text(teacher, student, body))
            res = {"ok": r["ok"], "dev": False, "error": r["error"]}
            if r["blocked"]:
                acc = db.scalar(select(TelegramAccount).where(TelegramAccount.chat_id == chat_id))
                if acc:
                    acc.blocked = True
        elif ch == "sms":
            res = send_sms(recipient, body)
        else:
            html = "<div style='font-family:Arial,sans-serif;white-space:pre-line'>" + body.replace("<", "&lt;") + "</div>"
            res = send_email(recipient, f"Learning English: {student.name}", html)
        status = "failed" if not res["ok"] else ("dev" if res["dev"] else "sent")
        db.add(
            ParentMessage(
                teacher_id=teacher.id, student_id=student.id, channel=ch, recipient=recipient[:255],
                body=body, status=status, error=(res.get("error") or None) and str(res["error"])[:300],
            )
        )
        results.append({"channel": ch, "recipient": recipient, "status": status})
    db.commit()
    if parent_link_id is not None and results[0]["status"] == "failed":
        raise AppError(502, "telegram_send_failed")
    return results
