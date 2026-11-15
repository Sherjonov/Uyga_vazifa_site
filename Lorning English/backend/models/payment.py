from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, Boolean, false
from sqlalchemy.orm import Mapped, mapped_column

from database import Base
from utils import utcnow


class Payment(Base):
    """O'qituvchining chekli obuna to'lovi va admin tekshiruv holati."""
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    months: Mapped[int] = mapped_column(Integer)
    amount: Mapped[int] = mapped_column(Integer)
    receipt_path: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(10), default="pending", index=True)  # pending | approved | rejected
    is_fraudulent: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    admin_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    period_start: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    period_end: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    previous_subscription_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
