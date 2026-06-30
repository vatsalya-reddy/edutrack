"""User & dashboard endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..database import get_db

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def create_user(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    """Create a user. A convenience endpoint so the API is usable end-to-end."""
    user = models.User(name=payload.name, email=payload.email)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email already registered")
    db.refresh(user)
    return user


@router.get("/{user_id}/dashboard", response_model=schemas.DashboardOut)
def dashboard(user_id: int, db: Session = Depends(get_db)):
    """Unified home-screen payload: profile, active-course progress, achievements."""
    try:
        return crud.build_dashboard(db, user_id)
    except crud.ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)
