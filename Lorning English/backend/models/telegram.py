from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint, false, text as sql_text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from utils import utcnow


class TelegramAccount(Base):
    """Botga /start bosgan har bir Telegram foydalanuvchisi (o'quvchi yoki ota-ona)."""
    __tablename__ = "telegram_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)  # shaxsiy chat id == Telegram user id
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    full_name: Mapped[str] = mapped_column(String(160), default="")
    # Telegram "Kontaktni ulashish" orqali tasdiqlangan telefon (+998...)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    # Saytdagi o'quvchi hisobi (o'quvchi sifatida ulangan bo'lsa)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    # Ota-ona hozir qaysi farzandni ko'rayotgani
    active_student_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    state_data: Mapped[dict] = mapped_column(JSON, default=dict, server_default=sql_text("'{}'"))
    blocked: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())  # bot bloklangan
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class ParentLink(Base):
    """Ota-ona (Telegram akkaunt) <-> farzand (o'quvchi). Bitta ota-onaning bir nechta farzandi bo'lishi mumkin."""
    __tablename__ = "parent_links"
    __table_args__ = (UniqueConstraint("telegram_account_id", "student_id", name="uq_parent_link"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_account_id: Mapped[int] = mapped_column(ForeignKey("telegram_accounts.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
