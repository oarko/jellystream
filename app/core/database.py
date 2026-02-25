"""Database configuration and session management."""

import os
from pathlib import Path
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

from app.core.config import settings

# Convert sqlite:/// to sqlite+aiosqlite:/// for async support
database_url = settings.DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://")

engine = create_async_engine(
    database_url,
    echo=settings.DEBUG,
    future=True
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


async def get_db() -> AsyncSession:
    """Get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database tables."""
    # Ensure database directory exists
    db_path = settings.DATABASE_URL.replace("sqlite:///", "")
    db_dir = os.path.dirname(db_path)
    if db_dir:
        Path(db_dir).mkdir(parents=True, exist_ok=True)

    # Import all models so SQLAlchemy registers them with Base.metadata
    # before create_all is called. Order matters for FK references.
    import app.models.stream          # legacy — kept for backward compat
    import app.models.schedule        # legacy — kept for backward compat
    import app.models.channel
    import app.models.channel_library
    import app.models.genre_filter
    import app.models.schedule_entry
    import app.models.collection
    import app.models.collection_item
    import app.models.channel_collection_source

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Safe column migrations — silently ignored if the column already exists
    _migrations = [
        "ALTER TABLE schedule_entries ADD COLUMN file_path TEXT",
        "ALTER TABLE schedule_entries ADD COLUMN description TEXT",
        "ALTER TABLE schedule_entries ADD COLUMN content_rating VARCHAR(20)",
        "ALTER TABLE schedule_entries ADD COLUMN thumbnail_path TEXT",
        "ALTER TABLE schedule_entries ADD COLUMN air_date VARCHAR(20)",
        "ALTER TABLE channels ADD COLUMN channel_type VARCHAR(20) DEFAULT 'video'",
        "ALTER TABLE genre_filters ADD COLUMN filter_type VARCHAR(10) DEFAULT 'include'",
    ]
    for stmt in _migrations:
        try:
            async with engine.begin() as conn:
                await conn.execute(text(stmt))
        except Exception:
            pass  # column already exists
