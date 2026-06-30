"""Database configuration.

Centralises the SQLAlchemy engine, session factory, declarative ``Base`` and the
FastAPI ``get_db`` dependency. Keeping this isolated means models, routes and the
seeding logic all share one source of truth for the connection.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# A file-based SQLite DB living next to the project root.
SQLALCHEMY_DATABASE_URL = "sqlite:///./edutrack.db"

# ``check_same_thread=False`` is required because FastAPI may use the connection
# across threads. SQLite is fine with this for a single-process prototype.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Declarative base shared by every ORM model."""


def get_db() -> Generator[Session, None, None]:
    """Yield a database session and guarantee it is closed afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
