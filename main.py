"""Application entrypoint.

Creates the FastAPI app, wires routers, and initialises + seeds the database on
startup via the lifespan handler.
"""

from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models, schemas
from .database import get_db
from .routers import analytics, enrollments, users
from .seed import init_and_seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables and load sample data before serving requests.
    init_and_seed()
    yield


app = FastAPI(
    title="EduTrack API",
    description="Micro-learning progress tracking, achievements and analytics.",
    version="1.0.0",
    lifespan=lifespan,
)

# Small read-only courses listing so clients can discover what's enrollable.
courses_router = APIRouter(prefix="/courses", tags=["courses"])


@courses_router.get("", response_model=list[schemas.CourseOut])
def list_courses(db: Session = Depends(get_db)):
    return db.scalars(select(models.Course).order_by(models.Course.id)).all()


@app.get("/", tags=["meta"])
def root():
    return {"service": "EduTrack API", "docs": "/docs", "status": "ok"}


app.include_router(courses_router)
app.include_router(users.router)
app.include_router(enrollments.router)
app.include_router(analytics.router)
