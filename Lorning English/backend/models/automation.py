from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, UniqueConstraint, false
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from utils import utcnow


class StudentPenalty(Base):
    __tablename__ = "student_penalties"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    points: Mapped[float] = mapped_column(Float, default=5.0)
    reason: Mapped[str] = mapped_column(String(80), default="parent_bot_not_linked")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ParentAlert(Base):
    """Ota-onaga yuborilgan avtomatik xabarlar jurnali: bir hodisa uchun ikki marta xabar yuborilmasligi uchun."""
    __tablename__ = "parent_alerts"
    __table_args__ = (UniqueConstraint("student_id", "kind", "ref", name="uq_parent_alert"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(20))   # attendance | hw_missed | danger
    ref: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class DangerZoneState(Base):
    __tablename__ = "danger_zone_states"
    __table_args__ = (UniqueConstraint("teacher_id", "student_id", name="uq_danger_zone_state"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    notified: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
