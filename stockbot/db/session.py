"""Database session management."""

from __future__ import annotations

from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

_engine = None


def get_engine(db_url: str = "sqlite:///data/stockbot.db"):
    """Get or create the database engine."""
    global _engine
    if _engine is None:
        _engine = create_engine(db_url, echo=False)
    return _engine


def init_db(db_url: str = "sqlite:///data/stockbot.db") -> None:
    """Initialize database tables."""
    import os

    os.makedirs("data", exist_ok=True)
    engine = get_engine(db_url)
    SQLModel.metadata.create_all(engine)


def get_session(db_url: str = "sqlite:///data/stockbot.db") -> Generator[Session, None, None]:
    """Yield a database session."""
    engine = get_engine(db_url)
    with Session(engine) as session:
        yield session
