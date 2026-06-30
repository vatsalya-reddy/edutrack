"""Analytics endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..database import get_db

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/leaderboard", response_model=list[schemas.LeaderboardEntry])
def get_leaderboard(db: Session = Depends(get_db)):
    """Top 5 users by total lessons completed (SQL aggregation, no Python sort)."""
    return crud.leaderboard(db, limit=5)
