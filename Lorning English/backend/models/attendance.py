from datetime import datetime, date
from typing import Optional

from sqlalchemy import String, Integer, Float, Date, DateTime, ForeignKey, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from utils import utcnow


class Attendance(Base):
    __tablename__ = "attendance"
    __table_args__ = (UniqueConstraint("group_id", "student_id", "date", name="uq_attendance"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    status: Mapped[str] = mapped_column(String(10))  # present | absent | excused
    # Belgilash paytidagi jarima. Status o'zgarsa qayta hisoblanadi, ikki marta ayrilmaydi.
    penalty_applied: Mapped[float] = mapped_column(Float, default=0.0)
    lesson_title: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class TeacherSettings(Base):
    __tablename__ = "teacher_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    absence_penalty: Mapped[float] = mapped_column(Float, default=5.0)  # Kelmadi: -5
    # Xavf zonasi chegaralari
    danger_missed_homework: Mapped[int] = mapped_column(Integer, default=3)
    danger_low_test_score: Mapped[float] = mapped_column(Float, default=5.0)
    danger_absences: Mapped[int] = mapped_column(Integer, default=3)
    danger_score_drop: Mapped[float] = mapped_column(Float, default=30.0)
    danger_inactive_days: Mapped[int] = mapped_column(Integer, default=7)
    # Jadvaldagi bir katakka qo'yiladigan eng katta ball (o'qituvchi o'zgartiradi)
    grid_max_score: Mapped[float] = mapped_column(Float, default=50.0, server_default=text("50"))
    # Davomat va vazifa jarimalari (Sozlamalarda o'zgaradi)
    late_penalty: Mapped[float] = mapped_column(Float, default=3.0, server_default=text("3"))          # Kech qoldi: -3
    hw_late_penalty: Mapped[float] = mapped_column(Float, default=5.0, server_default=text("5"))       # Vazifa kechikdi: -5
    hw_missing_penalty: Mapped[float] = mapped_column(Float, default=5.0, server_default=text("5"))    # Vazifa topshirilmadi: -5
    ai_daily_limit: Mapped[int] = mapped_column(Integer, default=8, server_default=text("8"))          # Ustoz AI: kuniga 8 ta so'rov
    similarity_threshold: Mapped[int] = mapped_column(Integer, default=70, server_default=text("70"))  # "Ko'chirgan" chegarasi (%)
    vocab_warning_limit: Mapped[int] = mapped_column(Integer, default=2, server_default=text("2"))     # Lug'at imtihonidagi ogohlantirishlar
    vocab_pass_percent: Mapped[int] = mapped_column(Integer, default=60, server_default=text("60"))    # Lug'atdan o'tish foizi
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
