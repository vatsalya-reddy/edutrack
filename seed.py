"""Database seeding.

Idempotent: running it more than once will not create duplicate courses. Invoked
automatically on startup (see main.py) and also runnable standalone:

    python -m app.seed
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import models
from .database import Base, SessionLocal, engine

SAMPLE_COURSES = [
    {"title": "Python Basics", "description": "Variables, loops and functions.", "total_lessons": 5},
    {"title": "Intro to FastAPI", "description": "Build your first REST API.", "total_lessons": 3},
    {"title": "SQL 101", "description": "Queries, joins and aggregation.", "total_lessons": 10},
]

SAMPLE_USERS = [
    {"name": "Ada Lovelace", "email": "ada@example.com"},
    {"name": "Alan Turing", "email": "alan@example.com"},
]


def seed(db: Session) -> None:
    """Insert sample data only if the relevant tables are empty."""
    course_count = db.scalar(select(func.count()).select_from(models.Course)) or 0
    if course_count == 0:
        db.add_all(models.Course(**c) for c in SAMPLE_COURSES)

    user_count = db.scalar(select(func.count()).select_from(models.User)) or 0
    if user_count == 0:
        db.add_all(models.User(**u) for u in SAMPLE_USERS)

    db.commit()


def init_and_seed() -> None:
    """Create tables (if missing) and seed. Safe to call on every startup."""
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed(db)


if __name__ == "__main__":
    init_and_seed()
    print("Database initialised and seeded -> edutrack.db")
