"""Kitoblar (dars kitobi / lug'at kitobi), lug'at unitlari va himoyalangan lug'at imtihoni natijalari."""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, false, text as sql_text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from utils import utcnow


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(10), index=True)  # lesson | vocab
    title: Mapped[str] = mapped_column(String(200))
    file_path: Mapped[str] = mapped_column(String(300))
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), index=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    units = relationship("VocabUnit", cascade="all, delete-orphan", order_by="VocabUnit.unit_number")


class VocabUnit(Base):
    __tablename__ = "vocab_units"

    id: Mapped[int] = mapped_column(primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id"), index=True)
    unit_number: Mapped[int] = mapped_column(Integer, default=1)
    title: Mapped[str] = mapped_column(String(200), default="")
    words: Mapped[list] = mapped_column(JSON, default=list)  # [{"en": "...", "uz": "..."}]
    teacher_opened: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())

    attempts = relationship("VocabAttempt", cascade="all, delete-orphan")
    retakes = relationship("VocabRetake", cascade="all, delete-orphan")


class VocabAttempt(Base):
    __tablename__ = "vocab_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("vocab_units.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(12), default="in_progress", index=True)  # in_progress | finished
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    score: Mapped[float] = mapped_column(Float, default=0.0)      # foiz / 10 (reytingga qo'shiladi)
    percent: Mapped[float] = mapped_column(Float, default=0.0)
    questions: Mapped[list] = mapped_column(JSON, default=list)   # to'g'ri javoblar bilan (faqat serverda)
    found: Mapped[list] = mapped_column(JSON, default=list)       # topilgan so'zlar
    missed: Mapped[list] = mapped_column(JSON, default=list)      # topilmagan so'zlar
    answers: Mapped[dict] = mapped_column(JSON, default=dict)     # savol id -> berilgan javob (bir marta, o'zgarmaydi)
    mistakes: Mapped[int] = mapped_column(Integer, default=0, server_default=sql_text("0"))
    stopped: Mapped[bool] = mapped_column(Boolean, default=False, server_default=sql_text("0"))  # 3 xatodan keyin to'xtatilgan
    warnings_count: Mapped[int] = mapped_column(Integer, default=0, server_default=sql_text("0"))
    violations: Mapped[list] = mapped_column(JSON, default=list)  # [{"kind": "...", "at": "..."}]
    kicked_out: Mapped[bool] = mapped_column(Boolean, default=False, server_default=sql_text("0"))
    photo_path: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class VocabFinalAttempt(Base):
    """Kitobning barcha unitlari topshirilgach ochiladigan yakuniy test (100 ta so'z, 10 tagacha xato, 3 urinish)."""
    __tablename__ = "vocab_final_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(12), default="in_progress", index=True)  # in_progress | finished
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    stopped: Mapped[bool] = mapped_column(Boolean, default=False)   # xato limiti oshib to'xtatilgan
    score: Mapped[float] = mapped_column(Float, default=0.0)        # o'tsa 25, bo'lmasa 0
    percent: Mapped[float] = mapped_column(Float, default=0.0)
    mistakes: Mapped[int] = mapped_column(Integer, default=0)
    warnings_count: Mapped[int] = mapped_column(Integer, default=0)
    strict: Mapped[bool] = mapped_column(Boolean, default=False)    # o'quvchi qat'iy (full screen) rejimni tanlaganmi
    questions: Mapped[list] = mapped_column(JSON, default=list)
    answers: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class VocabRetake(Base):
    __tablename__ = "vocab_retakes"

    id: Mapped[int] = mapped_column(primary_key=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("vocab_units.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    attempt_id: Mapped[Optional[int]] = mapped_column(ForeignKey("vocab_attempts.id", ondelete="SET NULL"), nullable=True)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(10), default="pending", index=True)  # pending | approved | rejected
    teacher_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
