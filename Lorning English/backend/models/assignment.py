from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Float, Text, DateTime, ForeignKey, UniqueConstraint, Boolean, JSON, text as sql_text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from utils import utcnow


class Assignment(Base):
    __tablename__ = "assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), index=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(10), index=True)  # homework | task | extra (darsdan tashqari)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    file_path: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # faqat task uchun
    max_score: Mapped[float] = mapped_column(Float, default=10.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    submissions = relationship("Submission", cascade="all, delete-orphan")


class Submission(Base):
    __tablename__ = "submissions"
    __table_args__ = (UniqueConstraint("assignment_id", "student_id", name="uq_submission"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    # Birinchi fayl file_path da, qolganlari shu yerda (bir nechta fayl yuklash mumkin)
    is_late: Mapped[bool] = mapped_column(Boolean, default=False, server_default=sql_text("0"))  # muddatdan keyin topshirilgan
    resubmit_count: Mapped[int] = mapped_column(Integer, default=0, server_default=sql_text("0"))
    penalty_points: Mapped[float] = mapped_column(Float, default=0.0, server_default=sql_text("0"))  # qayta yuborish jarimalari
    extra_files: Mapped[list] = mapped_column(JSON, default=list, server_default=sql_text("('[]')"))
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    # O'qituvchi "Tekshirish" ni bosganda AI tahlili shu yerda saqlanadi (yangi topshirilsa tozalanadi)
    ai_assessment: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # likely_ai | uncertain | likely_human
    ai_confidence: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ai_indicators: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    ai_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    similarity_matches: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    similarity_checked_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
