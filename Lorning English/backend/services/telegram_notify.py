"""Sayt hodisalari -> Telegram: vazifa baholanganda o'quvchi va uning ota-onalariga xabar."""
import threading
import traceback

from sqlalchemy import select

from database import SessionLocal
from models.assignment import Assignment, Submission
from models.telegram import ParentLink, TelegramAccount
from models.user import User
from services import bot_texts
from services import telegram_api as tg


def _notify_reviewed(submission_id: int) -> None:
    if not tg.is_configured():
        return
    with SessionLocal() as db:
        s = db.get(Submission, submission_id)
        if not s or s.score is None:
            return
        a = db.get(Assignment, s.assignment_id)
        student = db.get(User, s.student_id)
        if not a or not student:
            return
        own = db.scalars(select(TelegramAccount).where(TelegramAccount.user_id == student.id, TelegramAccount.blocked.is_(False))).all()
        parents = db.scalars(
            select(TelegramAccount).join(ParentLink, ParentLink.telegram_account_id == TelegramAccount.id)
            .where(ParentLink.student_id == student.id, TelegramAccount.blocked.is_(False))
        ).all()
        sent = set()
        for acc, for_parent in [(x, False) for x in own] + [(x, True) for x in parents]:
            if acc.chat_id in sent:
                continue
            sent.add(acc.chat_id)
            text = bot_texts.render_reviewed(student.name, a.title, s.score, a.max_score, s.comment, for_parent)
            r = tg.send_text(acc.chat_id, text)
            if r["blocked"]:
                acc.blocked = True
        db.commit()


def notify_reviewed_async(submission_id: int) -> None:
    """So'rovni sekinlashtirmaslik uchun alohida oqimda (xato bo'lsa e'tiborsiz)."""
    if not tg.is_configured():
        return

    def run() -> None:
        try:
            _notify_reviewed(submission_id)
        except Exception:  # noqa: BLE001
            traceback.print_exc()

    threading.Thread(target=run, daemon=True, name="tg-notify").start()
