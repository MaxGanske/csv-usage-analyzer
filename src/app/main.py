import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.api.reports import router as reports_router
from app.core.config import settings
from app.db.session import create_database_tables, engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Starting application and checking database tables")
    await create_database_tables()
    logger.info("Application startup complete")
    yield

app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(reports_router)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db", tags=["health"])
async def database_health() -> dict[str, str]:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    logger.info("Database health check passed")
    return {"status": "ok"}
