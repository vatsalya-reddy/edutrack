"""Enrollment & progress endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db

router = APIRouter(prefix="/enrollments", tags=["enrollments"])


@router.post("", response_model=schemas.EnrollmentOut, status_code=status.HTTP_201_CREATED)
def enroll(payload: schemas.EnrollmentCreate, db: Session = Depends(get_db)):
    """Enroll a user in a course; rejects duplicate active enrollments (400)."""
    try:
        return crud.create_enrollment(db, payload.user_id, payload.course_id)
    except crud.ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.post("/{enrollment_id}/complete-lesson", response_model=schemas.CompleteLessonResult)
def complete_lesson(enrollment_id: int, db: Session = Depends(get_db)):
    """Mark one more lesson complete.

    On reaching the course total, the enrollment is auto-completed and any
    achievements (Fast Starter / Deep Diver) are unlocked and reported back.
    """
    try:
        enrollment, newly_unlocked = crud.complete_lesson(db, enrollment_id)
    except crud.ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)

    return schemas.CompleteLessonResult(
        enrollment=enrollment,
        newly_unlocked_achievements=newly_unlocked,
    )
