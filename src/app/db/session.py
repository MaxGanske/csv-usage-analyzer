# Async SQLAlchemy engine, session factory, and request dependency.
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# Use the normalized URL so DigitalOcean's standard PostgreSQL URL works with asyncpg.
engine = create_async_engine(settings.async_database_url, pool_pre_ping=True)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session:
        yield session
