# FastAPI application entry point for the CSV usage analyzer.
# This module owns application startup, health checks, and router registration.
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.api.reports import router as reports_router
from app.core.config import settings
from app.db.session import create_database_tables, engine


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Create the initial database tables before accepting application traffic."""
    await create_database_tables()
    yield

app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(reports_router)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    """Return a lightweight liveness response without querying the database."""
    return {"status": "ok"}


@app.get("/health/db", tags=["health"])
async def database_health() -> dict[str, str]:
    """Verify that the configured PostgreSQL database accepts a simple query."""
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    return {"status": "ok"}
