"""Pydantic schemas (request bodies and response models).

These are the API's public contract — deliberately separate from the ORM models
so the storage layer can evolve without breaking clients. ``from_attributes`` lets
us build responses straight from ORM objects.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# --------------------------------------------------------------------------- #
# Users
# --------------------------------------------------------------------------- #
class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    email: EmailStr


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr
    created_at: datetime


# --------------------------------------------------------------------------- #
# Courses
# --------------------------------------------------------------------------- #
class CourseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    total_lessons: int


# --------------------------------------------------------------------------- #
# Enrollments
# --------------------------------------------------------------------------- #
class EnrollmentCreate(BaseModel):
    user_id: int
    course_id: int


class EnrollmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    course_id: int
    completed_lessons_count: int
    status: str
    started_at: datetime
    completed_at: datetime | None


class AchievementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    unlocked_at: datetime


class CompleteLessonResult(BaseModel):
    """Response for the complete-lesson action: the updated enrollment plus any
    achievements unlocked by this particular call."""

    enrollment: EnrollmentOut
    newly_unlocked_achievements: list[AchievementOut] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Dashboard & Analytics
# --------------------------------------------------------------------------- #
class ActiveCourseProgress(BaseModel):
    enrollment_id: int
    course_id: int
    course_title: str
    completed_lessons: int
    total_lessons: int
    progress_percentage: float


class DashboardOut(BaseModel):
    user: UserOut
    active_courses: list[ActiveCourseProgress]
    achievements: list[AchievementOut]


class LeaderboardEntry(BaseModel):
    user_id: int
    name: str
    total_lessons_completed: int
