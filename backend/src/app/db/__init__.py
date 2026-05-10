"""Database connection and session management."""
from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config.settings import get_settings


def get_database_url() -> str:
    """Build async database URL from settings."""
    settings = get_settings()
    db_path = settings.database_path
    db_dir = Path(db_path).parent
    db_dir.mkdir(parents=True, exist_ok=True)
    return f"sqlite+aiosqlite:///{db_path}"


async def create_db_engine() -> AsyncEngine:
    """Create async SQLAlchemy engine with optimizations."""
    url = get_database_url()
    engine = create_async_engine(
        url,
        echo=False,
        connect_args={
            "check_same_thread": False,
            "timeout": 30,
        },
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=3600,
    )

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """Enable WAL mode and foreign keys for SQLite."""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()

    return engine


async def get_session() -> AsyncSession:
    """Dependency: provide async database session."""
    from app.db.session import async_session_factory

    async with async_session_factory() as session:
        yield session


# Global session factory (initialized in lifespan)
async_session_factory: async_sessionmaker[AsyncSession] | None = None


async def init_db(force: bool = False) -> None:
    """Initialize database tables."""
    from app.models.base import Base

    global async_session_factory
    engine = await create_db_engine()
    async_session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        if force:
            await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    return engine


async def get_engine() -> AsyncEngine:
    """Get or create the database engine."""
    from app.db.session import async_session_factory as factory

    if factory is None:
        return await create_db_engine()
    return factory.kw["bind"]