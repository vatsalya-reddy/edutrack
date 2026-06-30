"""Service layer (CRUD + business rules).

Routes stay thin: they validate input and translate exceptions into HTTP codes.
All the interesting logic — duplicate-enrollment prevention, lesson completion,
achievement unlocking and the aggregation query — lives here so it can be reused
and tested in isolation.
"""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import models

# Achievement titles, kept as constants to avoid stringly-typed bugs.
FAST_STARTER = "Fast Starter"
DEEP_DIVER = "Deep Diver"
DEEP_DIVER_LESSON_THRESHOLD = 10


class ServiceError(Exception):
    """Domain error carrying an HTTP status code and message.

    Routes catch this and re-raise it as an HTTPException, keeping FastAPI
    imports out of the service layer.
    """

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


# --------------------------------------------------------------------------- #
# Lookups
# --------------------------------------------------------------------------- #
def get_user(db: Session, user_id: int) -> models.User:
    user = db.get(models.User, user_id)
    if user is None:
        raise ServiceError(404, f"User {user_id} not found")
    return user


def get_course(db: Session, course_id: int) -> models.Course:
    course = db.get(models.Course, course_id)
    if course is None:
        raise ServiceError(404, f"Course {course_id} not found")
    return course


def get_enrollment(db: Session, enrollment_id: int) -> models.Enrollment:
    enrollment = db.get(models.Enrollment, enrollment_id)
    if enrollment is None:
        raise ServiceError(404, f"Enrollment {enrollment_id} not found")
    return enrollment


# --------------------------------------------------------------------------- #
# Enrollment
# --------------------------------------------------------------------------- #
def create_enrollment(db: Session, user_id: int, course_id: int) -> models.Enrollment:
    """Enroll a user in a course, rejecting duplicate active enrollments."""
    get_user(db, user_id)          # 404 if missing
    get_course(db, course_id)      # 404 if missing

    existing = db.scalar(
        select(models.Enrollment).where(
            models.Enrollment.user_id == user_id,
            models.Enrollment.course_id == course_id,
            models.Enrollment.status == models.EnrollmentStatus.ACTIVE,
        )
    )
    if existing is not None:
        raise ServiceError(
            400, "User already has an active enrollment in this course"
        )

    enrollment = models.Enrollment(user_id=user_id, course_id=course_id)
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    return enrollment


def _has_achievement(db: Session, user_id: int, title: str) -> bool:
    return (
        db.scalar(
            select(func.count())
            .select_from(models.Achievement)
            .where(
                models.Achievement.user_id == user_id,
                models.Achievement.title == title,
            )
        )
        or 0
    ) > 0


def _award(db: Session, user_id: int, title: str) -> models.Achievement | None:
    """Grant an achievement once; return it if newly awarded, else None."""
    if _has_achievement(db, user_id, title):
        return None
    achievement = models.Achievement(user_id=user_id, title=title)
    db.add(achievement)
    return achievement


def complete_lesson(
    db: Session, enrollment_id: int
) -> tuple[models.Enrollment, list[models.Achievement]]:
    """Increment progress by one lesson and run completion/achievement logic.

    Returns the updated enrollment plus any achievements unlocked by this call.
    """
    enrollment = get_enrollment(db, enrollment_id)

    if enrollment.status == models.EnrollmentStatus.COMPLETED:
        raise ServiceError(400, "Course already completed for this enrollment")

    course = enrollment.course
    enrollment.completed_lessons_count += 1

    newly_unlocked: list[models.Achievement] = []

    if enrollment.completed_lessons_count >= course.total_lessons:
        # Clamp so we never report more completed than the course holds.
        enrollment.completed_lessons_count = course.total_lessons
        enrollment.status = models.EnrollmentStatus.COMPLETED
        enrollment.completed_at = datetime.now(timezone.utc)

        # Count completed courses *including* this one. We add 1 because this
        # enrollment's status change is not yet flushed/counted in the query.
        prior_completed = (
            db.scalar(
                select(func.count())
                .select_from(models.Enrollment)
                .where(
                    models.Enrollment.user_id == enrollment.user_id,
                    models.Enrollment.status == models.EnrollmentStatus.COMPLETED,
                    models.Enrollment.id != enrollment.id,
                )
            )
            or 0
        )

        # First-ever completed course -> Fast Starter.
        if prior_completed == 0:
            awarded = _award(db, enrollment.user_id, FAST_STARTER)
            if awarded:
                newly_unlocked.append(awarded)

        # Completed a course with >= 10 lessons -> Deep Diver.
        if course.total_lessons >= DEEP_DIVER_LESSON_THRESHOLD:
            awarded = _award(db, enrollment.user_id, DEEP_DIVER)
            if awarded:
                newly_unlocked.append(awarded)

    db.commit()
    db.refresh(enrollment)
    for ach in newly_unlocked:
        db.refresh(ach)
    return enrollment, newly_unlocked


# --------------------------------------------------------------------------- #
# Dashboard & Analytics
# --------------------------------------------------------------------------- #
def build_dashboard(db: Session, user_id: int) -> dict:
    """Assemble the unified dashboard payload for a user."""
    user = get_user(db, user_id)

    active_enrollments = db.scalars(
        select(models.Enrollment).where(
            models.Enrollment.user_id == user_id,
            models.Enrollment.status == models.EnrollmentStatus.ACTIVE,
        )
    ).all()

    active_courses = []
    for e in active_enrollments:
        total = e.course.total_lessons or 0
        pct = round((e.completed_lessons_count / total) * 100, 2) if total else 0.0
        active_courses.append(
            {
                "enrollment_id": e.id,
                "course_id": e.course_id,
                "course_title": e.course.title,
                "completed_lessons": e.completed_lessons_count,
                "total_lessons": total,
                "progress_percentage": pct,
            }
        )

    achievements = db.scalars(
        select(models.Achievement)
        .where(models.Achievement.user_id == user_id)
        .order_by(models.Achievement.unlocked_at)
    ).all()

    return {"user": user, "active_courses": active_courses, "achievements": achievements}


def leaderboard(db: Session, limit: int = 5) -> list[dict]:
    """Top users by total lessons completed across all courses.

    Aggregation happens entirely in SQL (SUM + GROUP BY + ORDER BY + LIMIT);
    there is no Python-side sorting.
    """
    total_lessons = func.coalesce(
        func.sum(models.Enrollment.completed_lessons_count), 0
    ).label("total_lessons_completed")

    rows = db.execute(
        select(models.User.id, models.User.name, total_lessons)
        .join(models.Enrollment, models.Enrollment.user_id == models.User.id)
        .group_by(models.User.id, models.User.name)
        .order_by(total_lessons.desc())
        .limit(limit)
    ).all()

    return [
        {"user_id": r.id, "name": r.name, "total_lessons_completed": int(r.total_lessons_completed)}
        for r in rows
    ]
