# Async SQLAlchemy database infrastructure for the application.
# The module centralizes the engine, initial table creation, and request sessions.
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.models import Base

# Use the normalized URL so DigitalOcean's standard PostgreSQL URL works with asyncpg.
engine = create_async_engine(settings.async_database_url, pool_pre_ping=True)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def create_database_tables() -> None:
    """Create missing initial tables without managing schema upgrades."""
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Yield one SQLAlchemy session and close it after the request completes."""
    async with async_session_factory() as session:
        yield session
