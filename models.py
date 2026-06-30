"""SQLAlchemy ORM models.

Defines the four core entities and the relationships between them. Foreign keys
and relationship() back-references keep navigation explicit and let SQLAlchemy
manage joins for us.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _utcnow() -> datetime:
    """Timezone-aware UTC timestamp (avoids the deprecated utcnow())."""
    return datetime.now(timezone.utc)


class EnrollmentStatus(str):
    """Lightweight string-enum of allowed enrollment states."""

    ACTIVE = "active"
    COMPLETED = "completed"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    enrollments: Mapped[list["Enrollment"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    achievements: Mapped[list["Achievement"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    total_lessons: Mapped[int] = mapped_column(Integer, nullable=False)

    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="course")


class Enrollment(Base):
    __tablename__ = "enrollments"
    # A user may only hold ONE active enrollment per course at a time. A partial
    # unique index enforces this at the DB level (guarding against races and
    # direct writes) while still allowing completed enrollments to repeat — e.g.
    # a user who finishes a course, re-enrolls, and finishes it again.
    __table_args__ = (
        Index(
            "uq_active_enrollment",
            "user_id",
            "course_id",
            unique=True,
            sqlite_where=text("status = 'active'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False, index=True)
    completed_lessons_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default=EnrollmentStatus.ACTIVE, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="enrollments")
    course: Mapped["Course"] = relationship(back_populates="enrollments")


class Achievement(Base):
    __tablename__ = "achievements"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    unlocked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    user: Mapped["User"] = relationship(back_populates="achievements")
