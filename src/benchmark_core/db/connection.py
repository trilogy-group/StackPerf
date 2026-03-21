"""Database connection management."""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


engine = None
async_session_factory = None


def init_db(database_url: str, echo: bool = False, pool_size: int = 5, max_overflow: int = 10) -> None:
    """Initialize database engine and session factory."""
    global engine, async_session_factory
    engine = create_async_engine(
        database_url,
        echo=echo,
        pool_size=pool_size,
        max_overflow=max_overflow,
    )
    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield database session."""
    if async_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    async with async_session_factory() as session:
        yield session


async def close_db() -> None:
    """Close database connections."""
    global engine
    if engine:
        await engine.dispose()
