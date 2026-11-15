from datetime import datetime

from typing import Optional

from sqlalchemy import String, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base
from utils import utcnow


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), index=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    pdf_path: Mapped[str] = mapped_column(String(300))
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    slides = relationship("LessonSlide", cascade="all, delete-orphan", order_by="LessonSlide.page_number")


class LessonSlide(Base):
    __tablename__ = "lesson_slides"

    id: Mapped[int] = mapped_column(primary_key=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), index=True)
    page_number: Mapped[int] = mapped_column(Integer)
    image_path: Mapped[str] = mapped_column(String(300))
    content: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # PDF dan qurilgan slayd (sarlavha, matn, kod, test)
