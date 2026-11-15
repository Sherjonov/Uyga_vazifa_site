from datetime import datetime
from typing import Optional

from sqlalchemy import String, Float, Boolean, DateTime, Integer, ForeignKey, select, func, true, false
from sqlalchemy import event
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from database import Base
from utils import utcnow


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), unique=True, index=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="student", index=True)  # student | teacher | admin
    track: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)  # school | university | circle
    language: Mapped[str] = mapped_column(String(2), default="uz")
    theme: Mapped[str] = mapped_column(String(10), default="light")
    onboarded: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)

    student_profile: Mapped[Optional["Student"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    teacher_profile: Mapped[Optional["Teacher"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    parent_contact: Mapped[Optional["ParentContact"]] = relationship(
        uselist=False, cascade="all, delete-orphan", foreign_keys="ParentContact.student_id"
    )

    @hybrid_property
    def claimed(self) -> bool:
        return self.student_profile.claimed if self.student_profile else True

    @claimed.setter
    def claimed(self, value: bool) -> None:
        if self.student_profile is None:
            self.student_profile = Student()
        self.student_profile.claimed = value

    @claimed.expression
    def claimed(cls):
        return func.coalesce(
            select(Student.claimed).where(Student.user_id == cls.id).scalar_subquery(), true()
        )

    @hybrid_property
    def total_score(self) -> float:
        return self.student_profile.total_score if self.student_profile else 0.0

    @total_score.setter
    def total_score(self, value: float) -> None:
        if self.student_profile is None:
            self.student_profile = Student()
        self.student_profile.total_score = value

    @total_score.expression
    def total_score(cls):
        return func.coalesce(
            select(Student.total_score).where(Student.user_id == cls.id).scalar_subquery(), 0.0
        )

    @hybrid_property
    def subscription_until(self) -> Optional[datetime]:
        subscription = self.teacher_profile.subscription if self.teacher_profile else None
        return subscription.subscription_until if subscription else None

    @subscription_until.setter
    def subscription_until(self, value: Optional[datetime]) -> None:
        self._ensure_subscription().subscription_until = value

    @subscription_until.expression
    def subscription_until(cls):
        return select(Subscription.subscription_until).where(Subscription.teacher_id == cls.id).scalar_subquery()

    @hybrid_property
    def trial_used(self) -> bool:
        subscription = self.teacher_profile.subscription if self.teacher_profile else None
        return subscription.trial_used if subscription else False

    @trial_used.setter
    def trial_used(self, value: bool) -> None:
        self._ensure_subscription().trial_used = value

    @trial_used.expression
    def trial_used(cls):
        return func.coalesce(
            select(Subscription.trial_used).where(Subscription.teacher_id == cls.id).scalar_subquery(), false()
        )

    @hybrid_property
    def has_paid(self) -> bool:
        subscription = self.teacher_profile.subscription if self.teacher_profile else None
        return subscription.has_paid if subscription else False

    @has_paid.setter
    def has_paid(self, value: bool) -> None:
        self._ensure_subscription().has_paid = value

    @has_paid.expression
    def has_paid(cls):
        return func.coalesce(
            select(Subscription.has_paid).where(Subscription.teacher_id == cls.id).scalar_subquery(), false()
        )

    @hybrid_property
    def fake_receipt_warning(self) -> bool:
        subscription = self.teacher_profile.subscription if self.teacher_profile else None
        return subscription.fake_receipt_warning if subscription else False

    @fake_receipt_warning.setter
    def fake_receipt_warning(self, value: bool) -> None:
        self._ensure_subscription().fake_receipt_warning = value

    @fake_receipt_warning.expression
    def fake_receipt_warning(cls):
        return func.coalesce(
            select(Subscription.fake_receipt_warning).where(Subscription.teacher_id == cls.id).scalar_subquery(), false()
        )

    def _ensure_subscription(self) -> "Subscription":
        if self.teacher_profile is None:
            self.teacher_profile = Teacher()
        if self.teacher_profile.subscription is None:
            self.teacher_profile.subscription = Subscription()
        return self.teacher_profile.subscription


class Student(Base):
    __tablename__ = "students"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    claimed: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true(), index=True)
    total_score: Mapped[float] = mapped_column(Float, default=0.0, server_default="0", index=True)
    claimed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)

    user: Mapped[User] = relationship(back_populates="student_profile")


class Teacher(Base):
    __tablename__ = "teachers"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)

    user: Mapped[User] = relationship(back_populates="teacher_profile")
    subscription: Mapped[Optional["Subscription"]] = relationship(
        back_populates="teacher", uselist=False, cascade="all, delete-orphan"
    )


class Subscription(Base):
    __tablename__ = "subscriptions"

    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.user_id", ondelete="CASCADE"), primary_key=True)
    subscription_until: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    trial_used: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    has_paid: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    fake_receipt_warning: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())

    teacher: Mapped[Teacher] = relationship(back_populates="subscription")


@event.listens_for(Session, "before_flush")
def ensure_role_profiles(session: Session, _flush_context, _instances) -> None:
    for user in session.new.union(session.dirty):
        if not isinstance(user, User):
            continue
        if user.role == "student":
            user.teacher_profile = None
            if user.student_profile is None:
                user.student_profile = Student()
        elif user.role == "teacher":
            user.student_profile = None
            if user.teacher_profile is None:
                user.teacher_profile = Teacher()
            if user.teacher_profile.subscription is None:
                user.teacher_profile.subscription = Subscription()
        else:
            user.student_profile = None
            user.teacher_profile = None


class OTPCode(Base):
    __tablename__ = "otp_codes"

    id: Mapped[int] = mapped_column(primary_key=True)
    channel: Mapped[str] = mapped_column(String(10))  # email | phone
    target: Mapped[str] = mapped_column(String(255), index=True)
    purpose: Mapped[str] = mapped_column(String(20), default="register")
    code_hash: Mapped[str] = mapped_column(String(64))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    consumed: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class ParentContact(Base):
    __tablename__ = "parent_contacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    parent_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
