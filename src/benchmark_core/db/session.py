"""Database session utilities for benchmark storage."""

import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from benchmark_core.db.models import Base


def get_database_url() -> str:
    """Get database URL from environment or use SQLite default."""
    # Default to SQLite for local development
    default_url = "sqlite:///./benchmark.db"
    # Check for PostgreSQL URL first
    pg_url = os.environ.get("BENCHMARK_DATABASE_URL")
    if pg_url:
        # Convert postgres:// to postgresql:// (SQLAlchemy requires postgresql://)
        if pg_url.startswith("postgres://"):
            pg_url = pg_url.replace("postgres://", "postgresql://", 1)
        return pg_url
    # Fallback to generic DATABASE_URL
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        # Convert postgres:// to postgresql:// (SQLAlchemy requires postgresql://)
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        return db_url
    return default_url


def create_database_engine(database_url: str | None = None) -> Engine:
    """Create a SQLAlchemy engine instance.

    Args:
        database_url: Optional database URL. If not provided, uses get_database_url().

    Returns:
        SQLAlchemy Engine instance.
    """
    if database_url is None:
        database_url = get_database_url()

    # For SQLite, we need special handling for datetime columns
    if database_url.startswith("sqlite"):
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            echo=False,
        )
    else:
        # PostgreSQL or other databases
        engine = create_engine(
            database_url,
            pool_pre_ping=True,  # Verify connections before use
            pool_recycle=300,  # Recycle connections after 5 minutes
            echo=False,
        )

    return engine


def init_db(engine: Engine | None = None) -> None:
    """Initialize database by creating all tables.

    Args:
        engine: Optional engine instance. If not provided, creates one.
    """
    if engine is None:
        engine = create_database_engine()

    Base.metadata.create_all(bind=engine)


def get_session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    """Get a session factory bound to an engine.

    Args:
        engine: Optional engine instance. If not provided, creates one.

    Returns:
        Session factory (sessionmaker).
    """
    if engine is None:
        engine = create_database_engine()

    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


@contextmanager
def get_db_session(
    engine: Engine | None = None,
) -> Generator[Session, None, None]:
    """Get a database session as a context manager.

    Usage:
        with get_db_session() as session:
            # use session here
            pass

    Args:
        engine: Optional engine instance. If not provided, creates one.

    Yields:
        SQLAlchemy Session instance.
    """
    session_factory = get_session_factory(engine)
    session = session_factory()

    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """Get database session generator for dependency injection (FastAPI pattern).

    Yields:
        SQLAlchemy Session instance.
    """
    session_factory = get_session_factory()
    session = session_factory()

    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
