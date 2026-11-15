from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from deps import get_db, require_role
from messages import AppError
from models.telegram import TelegramAccount
from models.user import User
from security import create_token
from services import telegram_api as tg

router = APIRouter(prefix="/telegram", tags=["telegram"])


@router.get("/info")
def info():
    """Bot sozlanganmi va havolasi (ro'yxatdan o'tish sahifasi, o'qituvchi sahifasi uchun)."""
    on = tg.is_configured()
    return {"enabled": on, "username": tg.bot_username() if on else None, "url": tg.bot_url() if on else None}


@router.get("/me")
def my_status(db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    acc = db.scalar(select(TelegramAccount).where(TelegramAccount.user_id == user.id))
    if not acc and user.phone:  # telefon bo'yicha ulangan bo'lishi mumkin
        acc = db.scalar(select(TelegramAccount).where(TelegramAccount.phone == user.phone))
    return {"enabled": tg.is_configured(), "linked": bool(acc and acc.user_id == user.id),
            "username": acc.username if acc else None, "url": tg.bot_url() if tg.is_configured() else None}


@router.post("/link-token")
def link_token(user: User = Depends(require_role("student"))):
    """Saytdagi hisobni Telegram botga ulash uchun 15 daqiqalik havola (telefon/email farqi yo'q)."""
    if not tg.is_configured():
        raise AppError(400, "telegram_not_configured")
    token = create_token(user.id, typ="tglink", minutes=15)
    return {"url": tg.bot_url(f"link_{token}"), "expires_in": 15 * 60}


@router.delete("/me")
def unlink_me(db: Session = Depends(get_db), user: User = Depends(require_role("student"))):
    for acc in db.scalars(select(TelegramAccount).where(TelegramAccount.user_id == user.id)).all():
        acc.user_id = None
    db.commit()
    return {"ok": True}
